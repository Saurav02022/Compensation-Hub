import json
import logging
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, Literal
from urllib.parse import urlencode

from pydantic import TypeAdapter, ValidationError
from sqlalchemy import Select, case, distinct, func, select
from sqlalchemy.orm import Session

from compensation_hub.analytics.service import SALARY_USD
from compensation_hub.ask_compensation.provider import PlannerContext, PlannerTurn, QueryPlanner
from compensation_hub.ask_compensation.schemas import (
    AskHistoryItem,
    AskResult,
    AskResultColumn,
    Calculation,
    DataField,
    DataQuery,
    FilterClause,
    PlannerResponse,
    Projection,
    QueryProgram,
    ResultFormat,
    ResultRef,
)
from compensation_hub.db.models import Compensation, Employee, FxRate
from compensation_hub.employees.service import list_filter_options

logger = logging.getLogger(__name__)

PLANNER_RESPONSE = TypeAdapter[PlannerResponse](PlannerResponse)
CENTS = Decimal("0.01")
PERCENT = Decimal("0.01")
DEFAULT_RESULT_LIMIT = 25
UNSUPPORTED_PREFIX = "I can't answer that from the data available in Compensation Hub."


class InvalidPlanError(Exception):
    """A generated program is valid JSON but cannot be executed safely or coherently."""


@dataclass(frozen=True)
class FieldInfo:
    expression: Any
    kind: Literal["text", "number", "boolean"]
    label: str
    default_format: ResultFormat
    monetary_usd: bool = False


HAS_COMPENSATION = case((Compensation.employee_id.is_not(None), True), else_=False)

FIELD_INFO: dict[DataField, FieldInfo] = {
    "employee_code": FieldInfo(Employee.employee_code, "text", "Employee code", "text"),
    "full_name": FieldInfo(Employee.full_name, "text", "Employee", "text"),
    "country": FieldInfo(Employee.country, "text", "Country", "text"),
    "department": FieldInfo(Employee.department, "text", "Department", "text"),
    "job_title": FieldInfo(Employee.job_title, "text", "Job title", "text"),
    "annual_salary": FieldInfo(Compensation.annual_salary, "number", "Annual salary", "number"),
    "currency_code": FieldInfo(Compensation.currency_code, "text", "Currency", "text"),
    "salary_usd": FieldInfo(SALARY_USD, "number", "Salary", "currency", monetary_usd=True),
    "rate_to_usd": FieldInfo(FxRate.rate_to_usd, "number", "Rate to USD", "number"),
    "has_compensation": FieldInfo(HAS_COMPENSATION, "boolean", "Has compensation", "text"),
}

CONTROLLED_FIELDS: dict[DataField, str] = {
    "country": "country",
    "department": "department",
    "job_title": "job title",
    "currency_code": "currency",
}


@dataclass(frozen=True)
class ExecutedColumn:
    key: str
    label: str
    format: ResultFormat
    currency: str | None = None


@dataclass(frozen=True)
class ExecutedQuery:
    name: str
    columns: tuple[ExecutedColumn, ...]
    raw_rows: tuple[dict[str, object], ...]
    result: AskResult


@dataclass(frozen=True)
class AskOutcome:
    status: Literal["answered", "unsupported"]
    answer: str
    interpretation: str | None = None
    plan: QueryProgram | None = None
    result: AskResult | None = None
    analytics_path: str | None = None


def _drop_nulls(value: object) -> object:
    if isinstance(value, dict):
        return {key: _drop_nulls(item) for key, item in value.items() if item is not None}
    if isinstance(value, list):
        return [_drop_nulls(item) for item in value]
    return value


def parse_planner_response(raw: str) -> PlannerResponse:
    try:
        payload = json.loads(raw.strip())
    except json.JSONDecodeError as error:
        raise InvalidPlanError(f"Planner response is not valid JSON: {error.msg}") from error
    try:
        return PLANNER_RESPONSE.validate_python(_drop_nulls(payload))
    except ValidationError as error:
        raise InvalidPlanError(
            f"Planner response failed validation: {error.error_count()} errors"
        ) from error


def _planner_context(session: Session) -> PlannerContext:
    options = list_filter_options(session)
    currencies = tuple(session.scalars(select(FxRate.currency_code).order_by(FxRate.currency_code)))
    pairs = session.execute(
        select(Employee.country, Compensation.currency_code)
        .join(Compensation, Compensation.employee_id == Employee.id)
        .distinct()
        .order_by(Employee.country, Compensation.currency_code)
    ).all()
    return PlannerContext(
        countries=options.countries,
        departments=options.departments,
        job_titles=options.job_titles,
        currency_codes=currencies,
        country_currencies=tuple((row[0], row[1]) for row in pairs),
    )


def _planner_history(history: list[AskHistoryItem]) -> tuple[PlannerTurn, ...]:
    return tuple(
        PlannerTurn(
            question=item.question,
            plan_json=json.dumps(item.plan.model_dump(mode="json"), separators=(",", ":")),
        )
        for item in history
    )


def _parse_decimal(value: str, *, field: DataField) -> Decimal:
    try:
        return Decimal(value)
    except InvalidOperation as error:
        raise InvalidPlanError(f"{field} requires a numeric filter value") from error


def _parse_boolean(value: str, *, field: DataField) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "yes", "1"}:
        return True
    if normalized in {"false", "no", "0"}:
        return False
    raise InvalidPlanError(f"{field} requires a boolean filter value")


def _typed_values(
    clause: FilterClause,
    *,
    salary_filter_rate: Decimal,
) -> list[str | Decimal | bool]:
    info = FIELD_INFO[clause.field]
    if info.kind == "number":
        values = [_parse_decimal(value, field=clause.field) for value in clause.values]
        if clause.field == "salary_usd" and salary_filter_rate != 1:
            return [value * salary_filter_rate for value in values]
        return values
    if info.kind == "boolean":
        return [_parse_boolean(value, field=clause.field) for value in clause.values]
    return list(clause.values)


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _apply_filter(
    statement: Select[Any],
    clause: FilterClause,
    *,
    salary_filter_rate: Decimal,
) -> Select[Any]:
    info = FIELD_INFO[clause.field]
    expression = info.expression

    if clause.op in ("is_null", "not_null"):
        if info.kind == "boolean":
            raise InvalidPlanError(f"{clause.op} is not meaningful for {clause.field}")
        predicate = expression.is_(None) if clause.op == "is_null" else expression.is_not(None)
        return statement.where(predicate)

    values = _typed_values(clause, salary_filter_rate=salary_filter_rate)

    if clause.op in ("contains", "starts_with", "ends_with"):
        if info.kind != "text":
            raise InvalidPlanError(f"{clause.op} is only valid for text fields")
        raw = str(values[0])
        escaped = _escape_like(raw)
        if clause.op == "contains":
            pattern = f"%{escaped}%"
        elif clause.op == "starts_with":
            pattern = f"{escaped}%"
        else:
            pattern = f"%{escaped}"
        return statement.where(expression.ilike(pattern, escape="\\"))

    if clause.op in ("gt", "gte", "lt", "lte") and info.kind != "number":
        raise InvalidPlanError(f"{clause.op} is only valid for numeric fields")

    if clause.op == "eq":
        return statement.where(expression == values[0])
    if clause.op == "neq":
        return statement.where(expression != values[0])
    if clause.op == "in":
        return statement.where(expression.in_(values))
    if clause.op == "not_in":
        return statement.where(expression.not_in(values))
    if clause.op == "gt":
        return statement.where(expression > values[0])
    if clause.op == "gte":
        return statement.where(expression >= values[0])
    if clause.op == "lt":
        return statement.where(expression < values[0])
    if clause.op == "lte":
        return statement.where(expression <= values[0])
    raise InvalidPlanError(f"Unsupported filter operator {clause.op}")


def _apply_filters(
    statement: Select[Any],
    filters: list[FilterClause],
    *,
    salary_filter_rate: Decimal,
) -> Select[Any]:
    for clause in filters:
        statement = _apply_filter(
            statement,
            clause,
            salary_filter_rate=salary_filter_rate,
        )
    return statement


def _base_select(*columns: Any) -> Select[Any]:
    return (
        select(*columns)
        .select_from(Employee)
        .outerjoin(Compensation, Compensation.employee_id == Employee.id)
        .outerjoin(FxRate, FxRate.currency_code == Compensation.currency_code)
    )


def _aggregate_expression(projection: Projection) -> Any:
    aggregate = projection.aggregate
    if aggregate is None:
        assert projection.field is not None
        return FIELD_INFO[projection.field].expression

    field_expression = (
        Employee.id if projection.field is None else FIELD_INFO[projection.field].expression
    )

    if aggregate == "count":
        return func.count(field_expression)
    if aggregate == "count_distinct":
        assert projection.field is not None
        return func.count(distinct(field_expression))
    if aggregate == "sum":
        return func.coalesce(func.sum(field_expression), 0)
    if aggregate == "avg":
        return func.avg(field_expression)
    if aggregate == "min":
        return func.min(field_expression)
    if aggregate == "max":
        return func.max(field_expression)
    if aggregate == "median":
        return func.percentile_cont(Decimal("0.5")).within_group(field_expression)
    if aggregate == "stddev":
        return func.stddev_pop(field_expression)
    if aggregate == "variance":
        return func.var_pop(field_expression)
    assert aggregate == "percentile"
    assert projection.percentile is not None
    return func.percentile_cont(projection.percentile).within_group(field_expression)


def _projection_format(projection: Projection) -> ResultFormat:
    if projection.aggregate in ("count", "count_distinct"):
        return "count"
    if projection.field is None:
        return "number"
    info = FIELD_INFO[projection.field]
    if info.monetary_usd:
        return "currency"
    if projection.aggregate is not None and info.kind == "number":
        return "number"
    return info.default_format


def _projection_label(projection: Projection) -> str:
    return projection.alias.replace("_", " ").strip().title()


def _query_has_exact_single_currency(query: DataQuery) -> bool:
    for clause in query.filters:
        if clause.field != "currency_code":
            continue
        if clause.op == "eq" and len(clause.values) == 1:
            return True
        if clause.op == "in" and len(clause.values) == 1:
            return True
    return False


def _validate_projection(projection: Projection, query: DataQuery) -> None:
    if projection.aggregate is None:
        return

    if projection.aggregate == "count":
        return
    if projection.aggregate == "count_distinct":
        if projection.field is None:
            raise InvalidPlanError("count_distinct requires a field")
        return

    assert projection.field is not None
    info = FIELD_INFO[projection.field]

    if projection.aggregate in ("sum", "avg", "median", "stddev", "variance", "percentile"):
        if info.kind != "number":
            raise InvalidPlanError(
                f"{projection.aggregate} is only valid for numeric fields"
            )
    elif projection.aggregate in ("min", "max") and info.kind == "boolean":
        raise InvalidPlanError(f"{projection.aggregate} is not valid for boolean fields")

    if projection.field == "annual_salary":
        if "currency_code" not in query.group_by and not _query_has_exact_single_currency(query):
            raise InvalidPlanError(
                "annual_salary cannot be aggregated across currencies; use salary_usd or "
                "filter/group by currency_code"
            )


def _validate_query(query: DataQuery) -> None:
    for projection in query.select:
        _validate_projection(projection, query)

    aggregate_projections = [p for p in query.select if p.aggregate is not None]
    plain_projections = [p for p in query.select if p.aggregate is None]

    if query.group_by and not aggregate_projections:
        raise InvalidPlanError("group_by requires at least one aggregate projection")

    if aggregate_projections:
        plain_fields = {p.field for p in plain_projections}
        group_fields = set(query.group_by)
        if plain_fields != group_fields:
            raise InvalidPlanError(
                "every non-aggregate selected field must appear in group_by, and every "
                "group_by field must be selected"
            )

    aliases = {projection.alias for projection in query.select}
    for order in query.order_by:
        if order.key not in aliases:
            raise InvalidPlanError(f"order_by key {order.key} is not a selected alias")

    uses_salary_usd = any(
        projection.field == "salary_usd" for projection in query.select
    ) or any(clause.field == "salary_usd" for clause in query.filters)
    if query.target_currency is not None and not uses_salary_usd:
        raise InvalidPlanError(
            "target_currency requires a salary_usd projection or filter"
        )


def _controlled_values(context: PlannerContext) -> dict[DataField, set[str]]:
    return {
        "country": set(context.countries),
        "department": set(context.departments),
        "job_title": set(context.job_titles),
        "currency_code": set(context.currency_codes),
    }


def _validate_program_values(program: QueryProgram, context: PlannerContext) -> None:
    known = _controlled_values(context)
    currencies = set(context.currency_codes)

    for query in program.queries:
        if query.target_currency is not None and query.target_currency not in currencies:
            raise InvalidPlanError(
                f"No exchange rate is configured for {query.target_currency}"
            )
        for clause in query.filters:
            if clause.field not in CONTROLLED_FIELDS:
                continue
            if clause.op not in ("eq", "neq", "in", "not_in"):
                continue
            unknown = sorted(
                value for value in clause.values if value not in known[clause.field]
            )
            if unknown:
                label = CONTROLLED_FIELDS[clause.field]
                raise InvalidPlanError(
                    f"No {label} value exists in the data for: {', '.join(unknown)}"
                )


def _currency_rate(session: Session, currency_code: str) -> Decimal:
    if currency_code == "USD":
        return Decimal("1")
    value = session.scalar(
        select(FxRate.rate_to_usd).where(FxRate.currency_code == currency_code)
    )
    if value is None:
        raise InvalidPlanError(f"No exchange rate is configured for {currency_code}")
    return Decimal(value)


def _money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(CENTS, rounding=ROUND_HALF_UP)


def _convert_usd(value: object, rate_to_usd: Decimal) -> Decimal:
    return (_money(value) / rate_to_usd).quantize(CENTS, rounding=ROUND_HALF_UP)


def _serialize_value(
    value: object,
    column: ExecutedColumn,
    *,
    rate_to_usd: Decimal,
) -> str | int | None:
    if value is None:
        return None
    if column.format == "count":
        return int(value)
    if column.format == "currency":
        return f"{_convert_usd(value, rate_to_usd):.2f}"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, Decimal):
        return format(value.normalize(), "f")
    if isinstance(value, (int, float)):
        return str(value)
    return str(value)


def _execute_query(session: Session, query: DataQuery) -> ExecutedQuery:
    _validate_query(query)

    selected: list[ColumnElement[Any]] = []
    selected_by_alias: dict[str, ColumnElement[Any]] = {}
    columns: list[ExecutedColumn] = []

    target_currency = query.target_currency or "USD"
    rate_to_usd = _currency_rate(session, target_currency)

    for projection in query.select:
        expression = _aggregate_expression(projection).label(projection.alias)
        selected.append(expression)
        selected_by_alias[projection.alias] = expression
        column_format = _projection_format(projection)
        columns.append(
            ExecutedColumn(
                key=projection.alias,
                label=_projection_label(projection),
                format=column_format,
                currency=target_currency if column_format == "currency" else None,
            )
        )

    statement = _apply_filters(
        _base_select(*selected),
        query.filters,
        salary_filter_rate=rate_to_usd,
    )

    if query.group_by:
        statement = statement.group_by(
            *(FIELD_INFO[field].expression for field in query.group_by)
        )

    if query.distinct:
        statement = statement.distinct()

    if query.order_by:
        ordering = []
        for order in query.order_by:
            expression = selected_by_alias[order.key]
            ordering.append(
                expression.desc().nulls_last()
                if order.direction == "desc"
                else expression.asc().nulls_last()
            )
        statement = statement.order_by(*ordering)
    elif query.group_by:
        statement = statement.order_by(
            *(FIELD_INFO[field].expression.asc().nulls_last() for field in query.group_by)
        )
    elif not any(projection.aggregate is not None for projection in query.select):
        if query.distinct:
            statement = statement.order_by(*selected)
        else:
            statement = statement.order_by(Employee.full_name, Employee.employee_code)

    scalar_aggregate = (
        not query.group_by
        and not query.distinct
        and all(projection.aggregate is not None for projection in query.select)
    )
    if not scalar_aggregate:
        statement = statement.limit(query.limit or DEFAULT_RESULT_LIMIT)

    raw_rows: list[dict[str, object]] = []
    serialized_rows: list[dict[str, str | int | None]] = []
    for row in session.execute(statement).mappings():
        raw = {column.key: row[column.key] for column in columns}
        raw_rows.append(raw)
        serialized_rows.append(
            {
                column.key: _serialize_value(
                    raw[column.key],
                    column,
                    rate_to_usd=rate_to_usd,
                )
                for column in columns
            }
        )

    result = AskResult(
        kind="scalar" if len(serialized_rows) == 1 and len(columns) == 1 else "table",
        currency=target_currency if any(column.format == "currency" for column in columns) else None,
        columns=[
            AskResultColumn(key=column.key, label=column.label, format=column.format)
            for column in columns
        ],
        rows=serialized_rows,
    )
    return ExecutedQuery(
        name=query.name,
        columns=tuple(columns),
        raw_rows=tuple(raw_rows),
        result=result,
    )


@dataclass(frozen=True)
class ReferencedValue:
    value: Decimal
    format: ResultFormat
    currency: str | None


def _reference_value(executed: dict[str, ExecutedQuery], ref: ResultRef) -> ReferencedValue:
    query = executed[ref.query]
    if len(query.raw_rows) != 1:
        raise InvalidPlanError(
            f"calculation reference {ref.query}.{ref.column} is not scalar"
        )
    column = next((column for column in query.columns if column.key == ref.column), None)
    if column is None:
        raise InvalidPlanError(
            f"calculation references unknown column {ref.query}.{ref.column}"
        )
    serialized = query.result.rows[0].get(ref.column)
    if serialized is None:
        raise InvalidPlanError(
            f"calculation reference {ref.query}.{ref.column} has no value"
        )
    try:
        value = Decimal(str(serialized))
    except InvalidOperation as error:
        raise InvalidPlanError(
            f"calculation reference {ref.query}.{ref.column} is not numeric"
        ) from error
    return ReferencedValue(value=value, format=column.format, currency=column.currency)


def _execute_calculation(
    calculation: Calculation,
    executed: dict[str, ExecutedQuery],
) -> AskResult:
    left = _reference_value(executed, calculation.left)
    right = _reference_value(executed, calculation.right)

    if calculation.op in ("divide", "percentage", "percent_difference", "ratio") and right.value == 0:
        raise InvalidPlanError("calculation cannot divide by zero")

    if calculation.op == "add":
        value = left.value + right.value
    elif calculation.op == "subtract":
        value = left.value - right.value
    elif calculation.op == "multiply":
        value = left.value * right.value
    elif calculation.op == "divide":
        value = left.value / right.value
    elif calculation.op == "percentage":
        value = (left.value / right.value) * 100
    elif calculation.op == "percent_difference":
        value = ((left.value - right.value) / abs(right.value)) * 100
    else:
        value = left.value / right.value

    result_format = calculation.format
    currency: str | None = None
    if result_format == "percent":
        value = value.quantize(PERCENT, rounding=ROUND_HALF_UP)
    elif result_format == "currency":
        currencies = {item.currency for item in (left, right) if item.currency is not None}
        if len(currencies) != 1:
            raise InvalidPlanError("currency calculation requires one consistent currency")
        currency = currencies.pop()
        value = value.quantize(CENTS, rounding=ROUND_HALF_UP)
    elif result_format == "count":
        value = value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    else:
        value = value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    serialized: str | int | None
    if result_format == "count":
        serialized = int(value)
    else:
        serialized = format(value, "f")

    return AskResult(
        kind="scalar",
        currency=currency,
        columns=[
            AskResultColumn(
                key="value",
                label=calculation.label,
                format=result_format,
            )
        ],
        rows=[{"value": serialized}],
    )


def _format_result_value(result: AskResult) -> str:
    if not result.rows or not result.columns:
        return "no matching data"
    column = result.columns[0]
    value = result.rows[0].get(column.key)
    if value is None:
        return "no value"
    if column.format == "currency":
        return f"{result.currency or 'USD'} {Decimal(str(value)):,.2f}"
    if column.format == "count":
        return f"{int(value):,}"
    if column.format == "percent":
        return f"{value}%"
    return str(value)


def _describe_filter(clause: FilterClause) -> str:
    label = FIELD_INFO[clause.field].label.lower()
    if clause.op == "eq":
        return f"{label} = {clause.values[0]}"
    if clause.op == "in":
        return f"{label} in {', '.join(clause.values)}"
    if clause.op == "contains":
        return f'{label} contains "{clause.values[0]}"'
    if clause.op == "starts_with":
        return f'{label} starts with "{clause.values[0]}"'
    if clause.op == "ends_with":
        return f'{label} ends with "{clause.values[0]}"'
    if clause.op == "is_null":
        return f"{label} is missing"
    if clause.op == "not_null":
        return f"{label} is present"
    return f"{label} {clause.op} {', '.join(clause.values)}"


def _interpretation(program: QueryProgram) -> str:
    if program.calculation is not None:
        return program.calculation.label

    query = program.queries[-1]
    selected = ", ".join(_projection_label(projection) for projection in query.select)
    parts = [selected]
    if query.filters:
        parts.append("for " + "; ".join(_describe_filter(clause) for clause in query.filters))
    if query.group_by:
        parts.append(
            "grouped by " + ", ".join(FIELD_INFO[field].label.lower() for field in query.group_by)
        )
    if query.target_currency is not None:
        parts.append(f"converted to {query.target_currency}")
    return ", ".join(parts)


def _answer_for_result(result: AskResult) -> str:
    if result.kind == "scalar" and len(result.rows) == 1 and len(result.columns) == 1:
        label = result.columns[0].label
        return f"{label}: {_format_result_value(result)}."
    return f"Derived {len(result.rows):,} row(s) from Compensation Hub data."


def _analytics_path(program: QueryProgram) -> str | None:
    if program.calculation is not None or len(program.queries) != 1:
        return None
    query = program.queries[0]
    if query.target_currency not in (None, "USD") or len(query.select) != 1:
        return None

    projection = query.select[0]
    metric: str | None = None
    if projection.aggregate == "count" and projection.field is None:
        metric = "headcount"
    elif projection.aggregate == "avg" and projection.field == "salary_usd":
        metric = "average"
    elif projection.aggregate == "sum" and projection.field == "salary_usd":
        metric = "payroll"
    if metric is None:
        return None

    if len(query.group_by) > 1:
        return None
    if query.group_by and query.group_by[0] not in ("country", "department", "job_title"):
        return None

    params: dict[str, str] = {"metric": metric}
    for clause in query.filters:
        if (
            clause.field not in ("country", "department", "job_title")
            or clause.op != "eq"
            or len(clause.values) != 1
        ):
            return None
        params[clause.field] = clause.values[0]
    if query.group_by:
        params["by"] = query.group_by[0]
    return "/analytics?" + urlencode(params)


def _execute_program(session: Session, program: QueryProgram) -> AskOutcome:
    executed: dict[str, ExecutedQuery] = {}
    for query in program.queries:
        executed[query.name] = _execute_query(session, query)

    if program.calculation is not None:
        result = _execute_calculation(program.calculation, executed)
    else:
        result = executed[program.queries[-1].name].result

    return AskOutcome(
        status="answered",
        answer=_answer_for_result(result),
        interpretation=_interpretation(program),
        plan=program,
        result=result,
        analytics_path=_analytics_path(program),
    )


def ask(
    session: Session,
    question: str,
    planner: QueryPlanner,
    history: list[AskHistoryItem] | None = None,
) -> AskOutcome:
    """Derive one read-only answer from available Compensation Hub data."""
    history = history or []
    context = _planner_context(session)
    raw = planner.plan(question, context, _planner_history(history))

    try:
        response = parse_planner_response(raw)
    except InvalidPlanError as error:
        logger.warning("Rejected planner response: %s", error)
        return AskOutcome(
            status="unsupported",
            answer=(
                f"{UNSUPPORTED_PREFIX} The question could not be mapped to a valid "
                "read-only query."
            ),
        )

    if response.status == "unsupported":
        return AskOutcome(
            status="unsupported",
            answer=f"{UNSUPPORTED_PREFIX} {response.reason}",
        )

    try:
        _validate_program_values(response.plan, context)
        return _execute_program(session, response.plan)
    except InvalidPlanError as error:
        logger.warning("Rejected executable Ask Compensation program: %s", error)
        return AskOutcome(
            status="unsupported",
            answer=f"{UNSUPPORTED_PREFIX} {error}",
        )
