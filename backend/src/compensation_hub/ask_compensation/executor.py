from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, Literal
from urllib.parse import urlencode

from sqlalchemy import Select, case, func, select
from sqlalchemy.orm import Session

from compensation_hub.analytics.service import SALARY_USD
from compensation_hub.ask_compensation.provider import PlannerContext
from compensation_hub.ask_compensation.schemas import (
    AskResult,
    AskResultColumn,
    Calculation,
    DataField,
    DataQuery,
    FilterClause,
    Projection,
    QueryProgram,
    ResultFormat,
    ResultRef,
)
from compensation_hub.db.models import Compensation, Employee, FxRate

CENTS = Decimal("0.01")
PERCENT = Decimal("0.01")
DEFAULT_ROW_LIMIT = 25
DEFAULT_GROUP_LIMIT = 100

FieldKind = Literal["text", "number", "boolean"]


class InvalidProgramError(Exception):
    """A validated plan still violates an executable data or safety constraint."""


@dataclass(frozen=True)
class FieldSpec:
    expression: Any
    kind: FieldKind
    normalized_money: bool = False
    local_money: bool = False


@dataclass(frozen=True)
class ColumnSpec:
    key: str
    label: str
    format: ResultFormat
    currency: str | None
    numeric: bool


@dataclass(frozen=True)
class ExecutedQuery:
    name: str
    rows: list[dict[str, object]]
    columns: list[ColumnSpec]
    currency: str | None


@dataclass(frozen=True)
class ExecutedProgram:
    result: AskResult
    answer: str
    interpretation: str
    analytics_path: str | None


def _field_spec(field: DataField) -> FieldSpec:
    specs: dict[DataField, FieldSpec] = {
        "employee_code": FieldSpec(Employee.employee_code, "text"),
        "full_name": FieldSpec(Employee.full_name, "text"),
        "country": FieldSpec(Employee.country, "text"),
        "department": FieldSpec(Employee.department, "text"),
        "job_title": FieldSpec(Employee.job_title, "text"),
        "annual_salary": FieldSpec(Compensation.annual_salary, "number", local_money=True),
        "currency_code": FieldSpec(Compensation.currency_code, "text"),
        "salary_usd": FieldSpec(SALARY_USD, "number", normalized_money=True),
        "rate_to_usd": FieldSpec(FxRate.rate_to_usd, "number"),
        "has_compensation": FieldSpec(
            case((Compensation.employee_id.is_not(None), True), else_=False),
            "boolean",
        ),
    }
    return specs[field]


def _base_select(*columns: Any) -> Select[Any]:
    return (
        select(*columns)
        .select_from(Employee)
        .outerjoin(Compensation, Compensation.employee_id == Employee.id)
        .outerjoin(FxRate, FxRate.currency_code == Compensation.currency_code)
    )


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _decimal(value: str, field: DataField) -> Decimal:
    try:
        return Decimal(value)
    except InvalidOperation as error:
        raise InvalidProgramError(f"{field} requires a numeric filter value") from error


def _boolean(value: str, field: DataField) -> bool:
    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise InvalidProgramError(f"{field} requires true or false")


def _typed_value(clause: FilterClause, value: str) -> object:
    kind = _field_spec(clause.field).kind
    if kind == "number":
        return _decimal(value, clause.field)
    if kind == "boolean":
        return _boolean(value, clause.field)
    return value


def _validate_operator(clause: FilterClause) -> None:
    kind = _field_spec(clause.field).kind
    text_ops = {"eq", "neq", "in", "not_in", "contains", "starts_with", "ends_with"}
    number_ops = {"eq", "neq", "in", "not_in", "gt", "gte", "lt", "lte"}
    bool_ops = {"eq", "neq"}
    nullable_ops = {"is_null", "not_null"}

    allowed = {
        "text": text_ops | nullable_ops,
        "number": number_ops | nullable_ops,
        "boolean": bool_ops,
    }[kind]
    if clause.op not in allowed:
        raise InvalidProgramError(f"{clause.op} is not valid for {clause.field}")


def _filter_expression(
    session: Session,
    clause: FilterClause,
    target_currency: str | None,
) -> Any:
    _validate_operator(clause)
    expression = _field_spec(clause.field).expression
    if clause.field == "salary_usd" and target_currency not in (None, "USD"):
        expression = expression / _rate_to_usd(session, target_currency)

    if clause.op == "is_null":
        return expression.is_(None)
    if clause.op == "not_null":
        return expression.is_not(None)

    values = [_typed_value(clause, value) for value in clause.values]
    if clause.op == "eq":
        return expression == values[0]
    if clause.op == "neq":
        return expression != values[0]
    if clause.op == "in":
        return expression.in_(values)
    if clause.op == "not_in":
        return expression.not_in(values)
    if clause.op in {"contains", "starts_with", "ends_with"}:
        escaped = _escape_like(str(values[0]))
        pattern = {
            "contains": f"%{escaped}%",
            "starts_with": f"{escaped}%",
            "ends_with": f"%{escaped}",
        }[clause.op]
        return expression.ilike(pattern, escape="\\")
    if clause.op == "gt":
        return expression > values[0]
    if clause.op == "gte":
        return expression >= values[0]
    if clause.op == "lt":
        return expression < values[0]
    if clause.op == "lte":
        return expression <= values[0]
    raise InvalidProgramError(f"Unsupported filter operator {clause.op}")


def _apply_filters(
    session: Session,
    statement: Select[Any],
    filters: list[FilterClause],
    target_currency: str | None,
) -> Select[Any]:
    for clause in filters:
        statement = statement.where(_filter_expression(session, clause, target_currency))
    return statement


def _controlled_values(context: PlannerContext) -> dict[DataField, set[str]]:
    return {
        "country": set(context.countries),
        "department": set(context.departments),
        "job_title": set(context.job_titles),
        "currency_code": set(context.currency_codes),
    }


def _validate_controlled_filters(query: DataQuery, context: PlannerContext) -> None:
    known = _controlled_values(context)
    for clause in query.filters:
        allowed = known.get(clause.field)
        if allowed is None or clause.op not in {"eq", "neq", "in", "not_in"}:
            continue
        unknown = sorted({value for value in clause.values if value not in allowed})
        if unknown:
            raise InvalidProgramError(
                f"No {clause.field.replace('_', ' ')} value exists for: {', '.join(unknown)}"
            )

    if query.target_currency is not None and query.target_currency not in set(
        context.currency_codes
    ):
        raise InvalidProgramError(f"No exchange rate is configured for {query.target_currency}")


def _single_currency_filter(query: DataQuery) -> bool:
    for clause in query.filters:
        if clause.field != "currency_code" or clause.op not in {"eq", "in"}:
            continue
        if len(clause.values) == 1:
            return True
    return False


def _validate_projection_shape(query: DataQuery) -> None:
    aggregates = [projection for projection in query.select if projection.aggregate is not None]
    plain = [projection for projection in query.select if projection.aggregate is None]

    if aggregates:
        plain_fields = {projection.field for projection in plain}
        grouped = set(query.group_by)
        if plain_fields != grouped:
            raise InvalidProgramError(
                "Every non-aggregate selected field must match the group_by fields"
            )
    elif query.group_by:
        raise InvalidProgramError("group_by requires at least one aggregate projection")

    selected_aliases = {projection.alias for projection in query.select}
    for order in query.order_by:
        if order.key not in selected_aliases:
            raise InvalidProgramError(f"order_by references unknown alias {order.key}")

    for projection in query.select:
        if projection.aggregate in {
            "sum",
            "avg",
            "median",
            "stddev",
            "variance",
            "percentile",
        }:
            assert projection.field is not None
            if _field_spec(projection.field).kind != "number":
                raise InvalidProgramError(f"{projection.aggregate} requires a numeric field")
        if projection.aggregate in {"min", "max"}:
            assert projection.field is not None
            if _field_spec(projection.field).kind == "boolean":
                raise InvalidProgramError(f"{projection.aggregate} is not valid for boolean fields")

        if (
            projection.field == "annual_salary"
            and projection.aggregate
            in {"sum", "avg", "min", "max", "median", "stddev", "variance", "percentile"}
            and "currency_code" not in query.group_by
            and not _single_currency_filter(query)
        ):
            raise InvalidProgramError(
                "annual_salary cannot be aggregated across currencies; use salary_usd "
                "or constrain/group by currency_code"
            )

    if query.target_currency is not None:
        uses_normalized_salary = any(
            projection.field == "salary_usd"
            and projection.aggregate not in {"count", "count_distinct"}
            for projection in query.select
        ) or any(clause.field == "salary_usd" for clause in query.filters)
        if not uses_normalized_salary:
            raise InvalidProgramError("target_currency requires a salary_usd projection or filter")


def _rate_to_usd(session: Session, currency_code: str) -> Decimal:
    rate = session.scalar(select(FxRate.rate_to_usd).where(FxRate.currency_code == currency_code))
    if rate is None:
        raise InvalidProgramError(f"No exchange rate is configured for {currency_code}")
    return Decimal(rate)


def _base_projection_expression(
    session: Session,
    projection: Projection,
    target_currency: str | None,
) -> tuple[Any, str | None]:
    if projection.field is None:
        return Employee.id, None

    spec = _field_spec(projection.field)
    expression = spec.expression
    currency: str | None = None
    if spec.normalized_money and projection.aggregate not in {"count", "count_distinct"}:
        currency = target_currency or "USD"
        if target_currency is not None and target_currency != "USD":
            expression = expression / _rate_to_usd(session, target_currency)
    return expression, currency


def _projection_expression(
    session: Session,
    projection: Projection,
    target_currency: str | None,
) -> tuple[Any, str | None]:
    base, currency = _base_projection_expression(session, projection, target_currency)
    aggregate = projection.aggregate

    if aggregate is None:
        return base.label(projection.alias), currency
    if aggregate == "count":
        source = Employee.id if projection.field is None else base
        return func.count(source).label(projection.alias), None
    if aggregate == "count_distinct":
        return func.count(func.distinct(base)).label(projection.alias), None
    if aggregate == "sum":
        return func.coalesce(func.sum(base), 0).label(projection.alias), currency
    if aggregate == "avg":
        return func.avg(base).label(projection.alias), currency
    if aggregate == "min":
        return func.min(base).label(projection.alias), currency
    if aggregate == "max":
        return func.max(base).label(projection.alias), currency
    if aggregate == "median":
        return func.percentile_cont(0.5).within_group(base).label(projection.alias), currency
    if aggregate == "stddev":
        return func.stddev_pop(base).label(projection.alias), currency
    if aggregate == "variance":
        return func.var_pop(base).label(projection.alias), currency
    if aggregate == "percentile":
        assert projection.percentile is not None
        return (
            func.percentile_cont(projection.percentile).within_group(base).label(projection.alias),
            currency,
        )
    raise InvalidProgramError(f"Unsupported aggregate {aggregate}")


def _human_label(alias: str) -> str:
    return alias.replace("_", " ").strip().title()


def _column_spec(
    projection: Projection,
    currency: str | None,
) -> ColumnSpec:
    if projection.aggregate in {"count", "count_distinct"}:
        return ColumnSpec(
            key=projection.alias,
            label=_human_label(projection.alias),
            format="count",
            currency=None,
            numeric=True,
        )

    field_kind = "number" if projection.field is None else _field_spec(projection.field).kind
    if currency is not None:
        result_format: ResultFormat = "currency"
    elif field_kind == "number":
        result_format = "number"
    else:
        result_format = "text"

    return ColumnSpec(
        key=projection.alias,
        label=_human_label(projection.alias),
        format=result_format,
        currency=currency,
        numeric=field_kind == "number",
    )


def _query_is_scalar(query: DataQuery) -> bool:
    return (
        bool(query.select)
        and all(projection.aggregate is not None for projection in query.select)
        and not query.group_by
    )


def _execute_query(
    session: Session,
    query: DataQuery,
    context: PlannerContext,
) -> ExecutedQuery:
    _validate_controlled_filters(query, context)
    _validate_projection_shape(query)

    expressions: list[Any] = []
    columns: list[ColumnSpec] = []
    currencies: set[str] = set()
    alias_expressions: dict[str, Any] = {}

    for projection in query.select:
        expression, currency = _projection_expression(session, projection, query.target_currency)
        expressions.append(expression)
        alias_expressions[projection.alias] = expression
        column = _column_spec(projection, currency)
        columns.append(column)
        if currency is not None:
            currencies.add(currency)

    statement = _apply_filters(
        session,
        _base_select(*expressions),
        query.filters,
        query.target_currency,
    )

    if query.group_by:
        statement = statement.group_by(*[_field_spec(field).expression for field in query.group_by])
    if query.distinct:
        statement = statement.distinct()

    for order in query.order_by:
        expression = alias_expressions[order.key]
        statement = statement.order_by(
            expression.desc().nulls_last()
            if order.direction == "desc"
            else expression.asc().nulls_last()
        )

    if not query.order_by and not _query_is_scalar(query):
        plain_employee_aliases = {
            projection.field: projection.alias
            for projection in query.select
            if projection.aggregate is None
        }
        if query.group_by:
            statement = statement.order_by(
                *[_field_spec(field).expression.asc().nulls_last() for field in query.group_by]
            )
        elif query.distinct:
            statement = statement.order_by(*expressions)
        elif "full_name" in plain_employee_aliases:
            statement = statement.order_by(Employee.full_name.asc(), Employee.employee_code.asc())
        elif "employee_code" in plain_employee_aliases:
            statement = statement.order_by(Employee.employee_code.asc())
        else:
            statement = statement.order_by(expressions[0].asc().nulls_last())

    if not _query_is_scalar(query):
        default_limit = (
            DEFAULT_GROUP_LIMIT if query.group_by or query.distinct else DEFAULT_ROW_LIMIT
        )
        statement = statement.limit(query.limit or default_limit)

    rows = [dict(row) for row in session.execute(statement).mappings()]
    result_currency = next(iter(currencies)) if len(currencies) == 1 else None
    return ExecutedQuery(
        name=query.name,
        rows=rows,
        columns=columns,
        currency=result_currency,
    )


def _normalize_numeric(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        raise InvalidProgramError("Boolean values cannot be used in calculations")
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))
    raise InvalidProgramError("Calculation references must be numeric")


def _resolve_ref(
    executed: dict[str, ExecutedQuery],
    ref: ResultRef,
) -> tuple[Decimal, ColumnSpec]:
    query = executed.get(ref.query)
    if query is None:
        raise InvalidProgramError(f"Calculation references unknown query {ref.query}")
    if len(query.rows) != 1:
        raise InvalidProgramError(f"Calculation query {ref.query} must return exactly one row")

    column = next((column for column in query.columns if column.key == ref.column), None)
    if column is None:
        raise InvalidProgramError(
            f"Calculation references unknown column {ref.column} in {ref.query}"
        )
    if not column.numeric:
        raise InvalidProgramError(f"Calculation column {ref.query}.{ref.column} is not numeric")
    value = query.rows[0].get(ref.column)
    if value is None:
        raise InvalidProgramError(f"Calculation column {ref.query}.{ref.column} has no value")
    return _normalize_numeric(value), column


def _execute_calculation(
    calculation: Calculation,
    executed: dict[str, ExecutedQuery],
) -> tuple[Decimal, str | None]:
    left, left_column = _resolve_ref(executed, calculation.left)
    right, right_column = _resolve_ref(executed, calculation.right)

    left_currency = left_column.currency
    right_currency = right_column.currency
    both_currency = left_currency is not None and right_currency is not None
    same_currency = both_currency and left_currency == right_currency

    if both_currency and not same_currency:
        raise InvalidProgramError("Deterministic arithmetic cannot combine different currencies")

    if calculation.op in {"add", "subtract"}:
        if (left_currency is None) != (right_currency is None):
            raise InvalidProgramError(f"{calculation.op} requires operands with compatible units")
    elif calculation.op == "multiply":
        if both_currency:
            raise InvalidProgramError("multiply cannot combine two monetary values")
    elif calculation.op == "divide":
        if left_currency is None and right_currency is not None:
            raise InvalidProgramError(
                "divide cannot divide a dimensionless value by a monetary value"
            )
    elif calculation.op in {"percentage", "percent_difference", "ratio"}:
        if (left_currency is None) != (right_currency is None):
            raise InvalidProgramError(
                f"{calculation.op} requires operands with compatible units"
            )

    if calculation.op in {"divide", "percentage", "percent_difference", "ratio"} and right == 0:
        raise InvalidProgramError("The requested calculation divides by zero")

    if calculation.op == "add":
        value = left + right
    elif calculation.op == "subtract":
        value = left - right
    elif calculation.op == "multiply":
        value = left * right
    elif calculation.op == "divide":
        value = left / right
    elif calculation.op == "percentage":
        value = (left / right) * 100
    elif calculation.op == "percent_difference":
        value = ((left - right) / abs(right)) * 100
    elif calculation.op == "ratio":
        value = left / right
    else:
        raise InvalidProgramError(f"Unsupported calculation operator {calculation.op}")

    expected_currency: str | None = None
    if calculation.op in {"add", "subtract"} and same_currency:
        expected_currency = left_currency
    elif calculation.op == "multiply":
        expected_currency = left_currency or right_currency
    elif calculation.op == "divide" and left_currency is not None and right_currency is None:
        expected_currency = left_currency

    if calculation.format == "currency":
        if expected_currency is None:
            raise InvalidProgramError("The requested calculation does not produce a monetary value")
        currency = expected_currency
    else:
        if expected_currency is not None:
            raise InvalidProgramError("A monetary calculation must use currency result formatting")
        currency = None

    if calculation.op in {"percentage", "percent_difference"} and calculation.format != "percent":
        raise InvalidProgramError(f"{calculation.op} must use percent result formatting")
    if calculation.op == "ratio" and calculation.format in {"currency", "percent", "count"}:
        raise InvalidProgramError("ratio must use numeric result formatting")

    return value, currency


def _serialized_value(value: object, column: ColumnSpec) -> str | int | None:
    if value is None:
        return None
    if column.format == "count":
        return int(value)
    if column.format == "currency":
        return f"{Decimal(str(value)).quantize(CENTS, rounding=ROUND_HALF_UP):.2f}"
    if column.format == "number":
        decimal_value = Decimal(str(value))
        return format(decimal_value.normalize(), "f")
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return str(value)


def _public_result(query: ExecutedQuery) -> AskResult:
    kind: Literal["scalar", "table"] = (
        "scalar" if len(query.rows) == 1 and len(query.columns) == 1 else "table"
    )
    return AskResult(
        kind=kind,
        currency=query.currency,
        columns=[
            AskResultColumn(
                key=column.key,
                label=column.label,
                format=column.format,
            )
            for column in query.columns
        ],
        rows=[
            {column.key: _serialized_value(row.get(column.key), column) for column in query.columns}
            for row in query.rows
        ],
    )


def _calculation_result(
    calculation: Calculation,
    value: Decimal,
    currency: str | None,
) -> AskResult:
    column = ColumnSpec(
        key="value",
        label=calculation.label,
        format=calculation.format,
        currency=currency,
        numeric=True,
    )
    return AskResult(
        kind="scalar",
        currency=currency,
        columns=[
            AskResultColumn(
                key=column.key,
                label=column.label,
                format=column.format,
            )
        ],
        rows=[{"value": _serialized_value(value, column)}],
    )


def _display_value(
    value: str | int | None,
    column: AskResultColumn,
    currency: str | None,
) -> str:
    if value is None:
        return "not available"
    if column.format == "count":
        return f"{int(value):,}"
    if column.format == "currency":
        return f"{currency or 'USD'} {Decimal(str(value)):,.2f}"
    if column.format == "percent":
        return f"{Decimal(str(value)).quantize(PERCENT, rounding=ROUND_HALF_UP):.2f}%"
    return str(value)


def _answer_for_result(result: AskResult) -> str:
    if result.kind == "scalar" and result.rows and result.columns:
        row = result.rows[0]
        column = result.columns[0]
        return f"{column.label}: {_display_value(row.get(column.key), column, result.currency)}."

    if len(result.rows) == 1 and result.columns:
        row = result.rows[0]
        parts = [
            f"{column.label}: {_display_value(row.get(column.key), column, result.currency)}"
            for column in result.columns
        ]
        return "; ".join(parts) + "."

    return f"Found {len(result.rows):,} result(s) from the available Compensation Hub data."


def _filter_description(clause: FilterClause) -> str:
    field = clause.field.replace("_", " ")
    if clause.op in {"is_null", "not_null"}:
        return f"{field} {clause.op.replace('_', ' ')}"
    value = ", ".join(clause.values)
    return f"{field} {clause.op.replace('_', ' ')} {value}"


def _query_description(query: DataQuery) -> str:
    selections = ", ".join(
        (
            f"{projection.aggregate} {projection.field or 'employees'}"
            if projection.aggregate is not None
            else str(projection.field)
        )
        for projection in query.select
    )
    text = selections
    if query.filters:
        text += " where " + "; ".join(_filter_description(clause) for clause in query.filters)
    if query.group_by:
        text += " grouped by " + ", ".join(field.replace("_", " ") for field in query.group_by)
    if query.target_currency is not None:
        text += f" converted to {query.target_currency}"
    return text


def _interpretation(program: QueryProgram) -> str:
    descriptions = [_query_description(query) for query in program.queries]
    if program.calculation is None:
        return descriptions[0]
    return f"{program.calculation.label}: " + " | ".join(descriptions)


def _analytics_path(program: QueryProgram) -> str | None:
    if program.calculation is not None or len(program.queries) != 1:
        return None
    query = program.queries[0]
    if query.target_currency not in (None, "USD"):
        return None
    if len(query.select) != 1:
        return None

    projection = query.select[0]
    metric: str | None = None
    if projection.aggregate == "count" and projection.field in (None, "employee_code"):
        metric = "headcount"
    elif projection.aggregate == "sum" and projection.field == "salary_usd":
        metric = "payroll"
    elif projection.aggregate == "avg" and projection.field == "salary_usd":
        metric = "average"
    if metric is None:
        return None

    if len(query.group_by) > 1:
        return None
    if query.group_by and query.group_by[0] not in {
        "country",
        "department",
        "job_title",
    }:
        return None

    params: dict[str, str] = {}
    for clause in query.filters:
        if (
            clause.field not in {"country", "department", "job_title"}
            or clause.op != "eq"
            or len(clause.values) != 1
        ):
            return None
        params[clause.field] = clause.values[0]

    if query.group_by:
        params["by"] = query.group_by[0]
    params["metric"] = metric
    return "/analytics?" + urlencode(params)


def execute_program(
    session: Session,
    program: QueryProgram,
    context: PlannerContext,
) -> ExecutedProgram:
    """Execute an approved read-only query program and format its grounded result."""
    if len(program.queries) > 1 and program.calculation is None:
        raise InvalidProgramError("Multiple queries require an explicit deterministic calculation")

    executed: dict[str, ExecutedQuery] = {}
    for query in program.queries:
        executed[query.name] = _execute_query(session, query, context)

    if program.calculation is not None:
        value, currency = _execute_calculation(program.calculation, executed)
        result = _calculation_result(program.calculation, value, currency)
    else:
        result = _public_result(executed[program.queries[0].name])

    return ExecutedProgram(
        result=result,
        answer=_answer_for_result(result),
        interpretation=_interpretation(program),
        analytics_path=_analytics_path(program),
    )
