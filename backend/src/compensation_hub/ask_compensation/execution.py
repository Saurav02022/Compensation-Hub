"""Runs a validated query as one bounded SELECT in PostgreSQL.

Queries read employees LEFT JOIN compensation LEFT JOIN fx_rates, the same shape and salary
normalization the analytics service uses, so an employee without compensation still counts as
an employee but contributes no salary. Every value from the plan is bound as a parameter;
column and table names come only from the catalog.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Literal

from sqlalchemy import (
    ColumnElement,
    Numeric,
    Select,
    and_,
    cast,
    distinct,
    func,
    literal,
    select,
    text,
)
from sqlalchemy.orm import Session

from compensation_hub.analytics.service import MissingFxRateError
from compensation_hub.ask_compensation.catalog import FieldSpec
from compensation_hub.ask_compensation.validation import (
    ResolvedCalculation,
    ResolvedCondition,
    ResolvedMeasure,
    Unit,
    ValidatedQuery,
)
from compensation_hub.db.models import Compensation, Employee, FxRate

STATEMENT_TIMEOUT = "5s"
CENTS = Decimal("0.01")
RATIO_PLACES = Decimal("0.0001")

ColumnType = Literal["text", "count", "money", "percent", "number"]
CellValue = str | int | Decimal | None


@dataclass(frozen=True)
class ResultColumn:
    key: str
    label: str
    type: ColumnType
    # The currency of a money column, or the key of the column that holds each row's currency.
    currency: str | None = None
    currency_key: str | None = None


@dataclass(frozen=True)
class ResultRow:
    values: tuple[CellValue, ...]
    employee_id: int | None = None


@dataclass(frozen=True)
class QueryResult:
    columns: tuple[ResultColumn, ...]
    rows: tuple[ResultRow, ...]
    total_rows: int


def begin_read_only(session: Session) -> None:
    """Start a transaction PostgreSQL itself refuses to write in, with a statement timeout.

    The query representation cannot express a write; this makes the database enforce it too.
    Must be the first statement of the transaction.
    """
    session.execute(text("SET TRANSACTION READ ONLY"))
    session.execute(text(f"SET LOCAL statement_timeout = '{STATEMENT_TIMEOUT}'"))


def ensure_fx_rates(session: Session) -> None:
    """Fail loudly if a stored salary cannot be normalized, rather than silently dropping it."""
    missing = session.scalars(
        select(Compensation.currency_code)
        .distinct()
        .outerjoin(FxRate, FxRate.currency_code == Compensation.currency_code)
        .where(FxRate.currency_code.is_(None))
    ).all()
    if missing:
        raise MissingFxRateError(missing)


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _condition(condition: ResolvedCondition) -> ColumnElement[bool]:
    column = condition.field.expression
    values = condition.values
    match condition.op:
        case "eq" if condition.field.kind == "text":
            return column.ilike(_escape_like(values[0]), escape="\\")
        case "contains":
            return column.ilike(f"%{_escape_like(values[0])}%", escape="\\")
        case "starts_with":
            return column.ilike(f"{_escape_like(values[0])}%", escape="\\")
        case "eq":
            return column == values[0]
        case "ne":
            return column != values[0]
        case "in":
            return column.in_(values)
        case "not_in":
            return column.not_in(values)
        case "gt":
            return column > condition.threshold_usd
        case "gte":
            return column >= condition.threshold_usd
        case "lt":
            return column < condition.threshold_usd
        case "lte":
            return column <= condition.threshold_usd
    raise ValueError(f"Unhandled operator {condition.op}")


def _base(
    columns: Sequence[ColumnElement[Any]], conditions: Sequence[ResolvedCondition]
) -> Select[Any]:
    statement = (
        select(*columns)
        .select_from(Employee)
        .outerjoin(Compensation, Compensation.employee_id == Employee.id)
        .outerjoin(FxRate, FxRate.currency_code == Compensation.currency_code)
    )
    for condition in conditions:
        statement = statement.where(_condition(condition))
    return statement


def _in_answer_currency(
    expression: ColumnElement[Any], query: ValidatedQuery
) -> ColumnElement[Any]:
    if query.target_rate == 1:
        return expression
    return expression / literal(query.target_rate, Numeric(18, 8))


def _label(spec: FieldSpec) -> str:
    return spec.label[0].upper() + spec.label[1:]


def _field_column(
    spec: FieldSpec, query: ValidatedQuery
) -> tuple[ColumnElement[Any], ResultColumn]:
    if spec.kind == "money":
        return _in_answer_currency(spec.expression, query), ResultColumn(
            spec.name, _label(spec), "money", currency=query.currency
        )
    if spec.kind == "local_money":
        return spec.expression, ResultColumn(
            spec.name, _label(spec), "money", currency_key="currency"
        )
    return spec.expression, ResultColumn(spec.name, _label(spec), "text")


def _measure(measure: ResolvedMeasure, query: ValidatedQuery) -> ColumnElement[Any]:
    source = measure.field.expression if measure.field is not None else Employee.id
    predicate = and_(*map(_condition, measure.conditions)) if measure.conditions else None

    def filtered(aggregate: Any) -> ColumnElement[Any]:
        result: ColumnElement[Any] = (
            aggregate.filter(predicate) if predicate is not None else aggregate
        )
        return result

    expression: ColumnElement[Any]
    match measure.function:
        case "count":
            expression = filtered(func.count(source))
        case "count_distinct":
            expression = filtered(func.count(distinct(source)))
        case "sum":
            # A total over no salaries is zero, matching the analytics payroll figure.
            expression = func.coalesce(filtered(func.sum(source)), 0)
        case "avg":
            expression = filtered(func.avg(source))
        case "min":
            expression = filtered(func.min(source))
        case "max":
            expression = filtered(func.max(source))
        case "median":
            # percentile_cont computes in double precision; averaging the lower and upper middle
            # values found by percentile_disc gives an exact NUMERIC median.
            lower = filtered(func.percentile_disc(0.5).within_group(source.asc()))
            upper = filtered(func.percentile_disc(0.5).within_group(source.desc()))
            expression = (lower + upper) / 2
        case _:
            raise ValueError(f"Unhandled function {measure.function}")

    if measure.unit == "money":
        expression = _in_answer_currency(expression, query)
    return expression


def _calculation(
    calculation: ResolvedCalculation, expressions: dict[str, ColumnElement[Any]]
) -> ColumnElement[Any]:
    def operand(value: str | Decimal) -> ColumnElement[Any]:
        if isinstance(value, Decimal):
            return literal(value, Numeric())
        # Counts are integers; cast so division is exact rather than integer division.
        return cast(expressions[value], Numeric())

    left, right = operand(calculation.left), operand(calculation.right)
    match calculation.op:
        case "add":
            return left + right
        case "subtract":
            return left - right
        case "multiply":
            return left * right
        case "divide":
            return left / func.nullif(right, 0)
        case "percent":
            return left * 100 / func.nullif(right, 0)
    raise ValueError(f"Unhandled operator {calculation.op}")


def _comparison(expression: ColumnElement[Any], op: str, value: Decimal) -> ColumnElement[bool]:
    match op:
        case "gt":
            return expression > value
        case "gte":
            return expression >= value
        case "lt":
            return expression < value
        case "lte":
            return expression <= value
        case "eq":
            return expression == value
        case "ne":
            return expression != value
    raise ValueError(f"Unhandled comparison {op}")


def _round(value: Any, unit: Unit) -> CellValue:
    if value is None:
        return None
    if unit == "count":
        return int(value)
    number = Decimal(str(value))
    places = RATIO_PLACES if unit == "number" else CENTS
    return number.quantize(places, rounding=ROUND_HALF_UP)


def _total(session: Session, statement: Select[Any], returned: int, limit: int | None) -> int:
    if limit is None or returned < limit:
        return returned
    counted = select(func.count()).select_from(statement.order_by(None).limit(None).subquery())
    return int(session.scalar(counted) or 0)


def _execute_rows(session: Session, query: ValidatedQuery) -> QueryResult:
    selected = [_field_column(spec, query) for spec in query.fields]
    columns = [expression.label(f"c{index}") for index, (expression, _) in enumerate(selected)]
    statement = _base([*columns, Employee.id.label("employee_id")], query.conditions)

    ordering = []
    for order in query.order:
        ordered = columns[[spec.name for spec in query.fields].index(order.key)]
        ordering.append(
            ordered.desc().nulls_last() if order.descending else ordered.asc().nulls_last()
        )
    # Employee codes are unique, so every page of rows has one deterministic order.
    statement = statement.order_by(*ordering, Employee.full_name, Employee.employee_code)
    statement = statement.limit(query.limit)

    result_columns = tuple(column for _, column in selected)
    rows = []
    for record in session.execute(statement):
        values: list[CellValue] = []
        for index, column in enumerate(result_columns):
            raw = record[index]
            values.append(_round(raw, "money") if column.type == "money" else raw)
        rows.append(ResultRow(tuple(values), employee_id=record.employee_id))

    total = _total(session, statement, len(rows), query.limit)
    return QueryResult(result_columns, tuple(rows), total)


def _execute_aggregate(session: Session, query: ValidatedQuery) -> QueryResult:
    group_columns: list[ColumnElement[Any]] = [
        spec.expression.label(f"g{index}") for index, spec in enumerate(query.group_by)
    ]

    expressions: dict[str, ColumnElement[Any]] = {}
    units: dict[str, Unit] = {}
    for measure in query.measures:
        expressions[measure.name] = _measure(measure, query)
        units[measure.name] = measure.unit
    for calculation in query.calculations:
        expressions[calculation.name] = _calculation(calculation, expressions)
        units[calculation.name] = calculation.unit

    names = list(expressions)
    labelled = [expressions[name].label(f"m{index}") for index, name in enumerate(names)]
    statement = _base([*group_columns, *labelled], query.conditions)
    if query.group_by:
        statement = statement.group_by(*(spec.expression for spec in query.group_by))
    for condition in query.having:
        statement = statement.having(
            _comparison(expressions[condition.key], condition.op, condition.value)
        )

    by_key = {spec.name: column for spec, column in zip(query.group_by, group_columns, strict=True)}
    by_key.update(zip(names, labelled, strict=True))
    ordering = [
        by_key[order.key].desc().nulls_last()
        if order.descending
        else by_key[order.key].asc().nulls_last()
        for order in query.order
    ]
    statement = statement.order_by(*ordering, *(spec.expression for spec in query.group_by))
    if query.limit is not None:
        statement = statement.limit(query.limit)

    labels = query.labels()
    result_columns = [ResultColumn(spec.name, _label(spec), "text") for spec in query.group_by]
    for name in names:
        unit = units[name]
        currency = query.currency if unit == "money" else None
        result_columns.append(ResultColumn(name, labels[name], unit, currency=currency))

    rows = []
    for record in session.execute(statement):
        values: list[CellValue] = list(record[: len(group_columns)])
        values.extend(
            _round(record[len(group_columns) + index], units[name])
            for index, name in enumerate(names)
        )
        rows.append(ResultRow(tuple(values)))

    total = _total(session, statement, len(rows), query.limit)
    return QueryResult(tuple(result_columns), tuple(rows), total)


def execute_query(session: Session, query: ValidatedQuery) -> QueryResult:
    if query.kind == "rows":
        return _execute_rows(session, query)
    return _execute_aggregate(session, query)
