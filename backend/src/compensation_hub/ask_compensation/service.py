import json
import logging
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Literal

from pydantic import TypeAdapter, ValidationError
from sqlalchemy import ColumnElement, Select, and_, case, distinct, func, select
from sqlalchemy.orm import InstrumentedAttribute, Session

from compensation_hub.analytics.service import SALARY_USD
from compensation_hub.ask_compensation.provider import PlannerContext, PlannerTurn, QueryPlanner
from compensation_hub.ask_compensation.schemas import (
    AggregateExpression,
    AskHistoryItem,
    AskResult,
    AskResultColumn,
    BinaryExpression,
    CurrencyExpression,
    Expression,
    FieldExpression,
    LiteralExpression,
    PlannerResponse,
    Predicate,
    QueryPlan,
    SelectItem,
)
from compensation_hub.db.models import Compensation, Employee, FxRate
from compensation_hub.employees.service import list_filter_options

logger = logging.getLogger(__name__)

PLANNER_RESPONSE = TypeAdapter[PlannerResponse](PlannerResponse)
CENTS = Decimal("0.01")

FIELD_COLUMNS: dict[str, InstrumentedAttribute[Any] | ColumnElement[Any]] = {
    "employee_code": Employee.employee_code,
    "full_name": Employee.full_name,
    "country": Employee.country,
    "department": Employee.department,
    "job_title": Employee.job_title,
    "annual_salary": Compensation.annual_salary,
    "currency_code": Compensation.currency_code,
    "salary_usd": SALARY_USD,
    "rate_to_usd": FxRate.rate_to_usd,
}

TEXT_FIELDS = {
    "employee_code",
    "full_name",
    "country",
    "department",
    "job_title",
    "currency_code",
}
NUMERIC_FIELDS = {"annual_salary", "salary_usd", "rate_to_usd"}

UNSUPPORTED_PREFIX = "I can't answer that from the data available in Compensation Hub."


class InvalidPlanError(Exception):
    """The planner output cannot be executed safely by the generic read-only query engine."""


@dataclass(frozen=True)
class AskOutcome:
    status: Literal["answered", "unsupported"]
    answer: str
    interpretation: str | None = None
    plan: QueryPlan | None = None
    result: AskResult | None = None


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
    return PlannerContext(
        countries=options.countries,
        departments=options.departments,
        job_titles=options.job_titles,
        currency_codes=currencies,
    )


def _planner_history(history: list[AskHistoryItem]) -> tuple[PlannerTurn, ...]:
    return tuple(
        PlannerTurn(
            question=item.question,
            plan_json=json.dumps(item.plan.model_dump(mode="json"), separators=(",", ":")),
        )
        for item in history
    )


def _coerce_value(field: str, value: object) -> object:
    if field in TEXT_FIELDS:
        if not isinstance(value, str):
            raise InvalidPlanError(f"{field} requires a text value")
        return value
    if field in NUMERIC_FIELDS:
        if isinstance(value, bool):
            raise InvalidPlanError(f"{field} requires a numeric value")
        try:
            return Decimal(str(value))
        except Exception as error:
            raise InvalidPlanError(f"{field} requires a numeric value") from error
    raise InvalidPlanError(f"Unknown field: {field}")


def _predicate_expression(predicate: Predicate) -> ColumnElement[bool]:
    column = FIELD_COLUMNS[predicate.field]
    operator = predicate.operator

    if operator == "is_null":
        return column.is_(None)
    if operator == "is_not_null":
        return column.is_not(None)

    if operator == "in":
        values = [_coerce_value(predicate.field, value) for value in predicate.values]
        return column.in_(values)

    assert predicate.value is not None
    value = _coerce_value(predicate.field, predicate.value)

    if operator == "equals":
        return column == value
    if operator == "not_equals":
        return column != value
    if operator == "contains":
        if predicate.field not in TEXT_FIELDS:
            raise InvalidPlanError("contains can only be used with text fields")
        escaped = str(value).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        return column.ilike(f"%{escaped}%", escape="\\")
    if operator == "greater_than":
        return column > value
    if operator == "greater_than_or_equal":
        return column >= value
    if operator == "less_than":
        return column < value
    if operator == "less_than_or_equal":
        return column <= value
    raise InvalidPlanError(f"Unsupported predicate operator: {operator}")


def _predicate_list(predicates: list[Predicate]) -> list[ColumnElement[bool]]:
    return [_predicate_expression(predicate) for predicate in predicates]


def _expression_depth(expression: Expression) -> int:
    if isinstance(expression, (FieldExpression, AggregateExpression, LiteralExpression)):
        return 1
    if isinstance(expression, BinaryExpression):
        return 1 + max(_expression_depth(expression.left), _expression_depth(expression.right))
    if isinstance(expression, CurrencyExpression):
        return 1 + _expression_depth(expression.expression)
    return 1


def _contains_salary_usd(expression: Expression) -> bool:
    if isinstance(expression, FieldExpression):
        return expression.field == "salary_usd"
    if isinstance(expression, AggregateExpression):
        return expression.field == "salary_usd"
    if isinstance(expression, BinaryExpression):
        return _contains_salary_usd(expression.left) or _contains_salary_usd(expression.right)
    if isinstance(expression, CurrencyExpression):
        return _contains_salary_usd(expression.expression)
    return False


def _currency_code(expression: Expression) -> str | None:
    if isinstance(expression, CurrencyExpression):
        return expression.currency_code
    if _contains_salary_usd(expression):
        return "USD"
    return None


def _compile_aggregate(expression: AggregateExpression) -> ColumnElement[Any]:
    where = _predicate_list(expression.where)

    if expression.function == "count":
        if expression.field is None:
            aggregate: ColumnElement[Any] = func.count(Employee.id)
        else:
            field = FIELD_COLUMNS[expression.field]
            aggregate = func.count(distinct(field)) if expression.distinct else func.count(field)
        if where:
            aggregate = aggregate.filter(and_(*where))
        return aggregate

    assert expression.field is not None
    field = FIELD_COLUMNS[expression.field]

    if expression.function == "median":
        ordered = field
        if where:
            ordered = case((and_(*where), field), else_=None)
        return func.percentile_cont(0.5).within_group(ordered)

    aggregate_fn = {
        "sum": func.sum,
        "average": func.avg,
        "minimum": func.min,
        "maximum": func.max,
    }[expression.function]
    aggregate = aggregate_fn(field)
    if where:
        aggregate = aggregate.filter(and_(*where))
    return aggregate


def _compile_expression(
    session: Session,
    expression: Expression,
    *,
    depth: int = 0,
) -> ColumnElement[Any]:
    if depth > 6:
        raise InvalidPlanError("Expression is too deeply nested")

    if isinstance(expression, FieldExpression):
        return FIELD_COLUMNS[expression.field]

    if isinstance(expression, AggregateExpression):
        return _compile_aggregate(expression)

    if isinstance(expression, LiteralExpression):
        return select(expression.value).scalar_subquery()

    if isinstance(expression, BinaryExpression):
        left = _compile_expression(session, expression.left, depth=depth + 1)
        right = _compile_expression(session, expression.right, depth=depth + 1)
        if expression.operator == "add":
            return left + right
        if expression.operator == "subtract":
            return left - right
        if expression.operator == "multiply":
            return left * right
        if expression.operator == "divide":
            return left / func.nullif(right, 0)
        raise InvalidPlanError(f"Unsupported binary operator: {expression.operator}")

    if isinstance(expression, CurrencyExpression):
        if not _contains_salary_usd(expression.expression):
            raise InvalidPlanError(
                "Currency conversion must wrap a salary_usd-based monetary expression"
            )
        rate = session.scalar(
            select(FxRate.rate_to_usd).where(FxRate.currency_code == expression.currency_code)
        )
        if rate is None:
            raise InvalidPlanError(f"No exchange rate is configured for {expression.currency_code}")
        inner = _compile_expression(session, expression.expression, depth=depth + 1)
        return inner / Decimal(rate)

    raise InvalidPlanError("Unknown expression kind")


def _has_aggregate(expression: Expression) -> bool:
    if isinstance(expression, AggregateExpression):
        return True
    if isinstance(expression, BinaryExpression):
        return _has_aggregate(expression.left) or _has_aggregate(expression.right)
    if isinstance(expression, CurrencyExpression):
        return _has_aggregate(expression.expression)
    return False


def _selected_fields(expression: Expression) -> set[str]:
    if isinstance(expression, FieldExpression):
        return {expression.field}
    if isinstance(expression, BinaryExpression):
        return _selected_fields(expression.left) | _selected_fields(expression.right)
    if isinstance(expression, CurrencyExpression):
        return _selected_fields(expression.expression)
    return set()


def _validate_plan_semantics(plan: QueryPlan, context: PlannerContext) -> None:
    known_dimension_values = {
        "country": set(context.countries),
        "department": set(context.departments),
        "job_title": set(context.job_titles),
        "currency_code": set(context.currency_codes),
    }

    all_predicates = list(plan.where)
    for item in plan.select:
        if _expression_depth(item.expression) > 6:
            raise InvalidPlanError("Expression is too deeply nested")

        def collect(expression: Expression) -> None:
            if isinstance(expression, AggregateExpression):
                all_predicates.extend(expression.where)
            elif isinstance(expression, BinaryExpression):
                collect(expression.left)
                collect(expression.right)
            elif isinstance(expression, CurrencyExpression):
                if expression.currency_code not in set(context.currency_codes):
                    raise InvalidPlanError(
                        f"No exchange rate is configured for {expression.currency_code}"
                    )
                collect(expression.expression)

        collect(item.expression)

    for predicate in all_predicates:
        if predicate.field not in known_dimension_values:
            continue
        allowed = known_dimension_values[predicate.field]
        values = predicate.values if predicate.operator == "in" else [predicate.value]
        for value in values:
            if isinstance(value, str) and value not in allowed:
                raise InvalidPlanError(
                    f"No {predicate.field.replace('_', ' ')} value exists in the data for {value}"
                )

    has_any_aggregate = any(_has_aggregate(item.expression) for item in plan.select)
    if has_any_aggregate:
        grouped = set(plan.group_by)
        for item in plan.select:
            for field in _selected_fields(item.expression):
                if field not in grouped:
                    raise InvalidPlanError(
                        f"Field {field} must be grouped when selected with aggregates"
                    )

    if plan.group_by:
        for field in plan.group_by:
            if field in ("annual_salary", "salary_usd", "rate_to_usd"):
                raise InvalidPlanError("Grouping by continuous monetary fields is not supported")

    if not has_any_aggregate and not plan.group_by and plan.limit > 100:
        raise InvalidPlanError("Row-returning queries must remain bounded")


def _base_query() -> Select[Any]:
    return (
        select()
        .select_from(Employee)
        .outerjoin(Compensation, Compensation.employee_id == Employee.id)
        .outerjoin(FxRate, FxRate.currency_code == Compensation.currency_code)
    )


def _format_decimal(value: object) -> str:
    return f"{Decimal(str(value)).quantize(CENTS, rounding=ROUND_HALF_UP):.2f}"


def _serialize_cell(value: object, format_kind: str) -> str | int | None:
    if value is None:
        return None
    if format_kind == "count":
        return int(value)
    if format_kind in ("currency", "number", "percent"):
        return _format_decimal(value)
    return str(value)


def _execute_plan(session: Session, plan: QueryPlan) -> AskResult:
    context = _planner_context(session)
    _validate_plan_semantics(plan, context)

    compiled: list[tuple[SelectItem, ColumnElement[Any]]] = []
    for item in plan.select:
        expression = _compile_expression(session, item.expression).label(item.alias)
        compiled.append((item, expression))

    statement = (
        select(*(expression for _, expression in compiled))
        .select_from(Employee)
        .outerjoin(Compensation, Compensation.employee_id == Employee.id)
        .outerjoin(FxRate, FxRate.currency_code == Compensation.currency_code)
    )

    predicates = _predicate_list(plan.where)
    if predicates:
        statement = statement.where(and_(*predicates))

    if plan.group_by:
        statement = statement.group_by(*(FIELD_COLUMNS[field] for field in plan.group_by))

    if plan.distinct:
        statement = statement.distinct()

    aliases = {item.alias: expression for item, expression in compiled}
    for ordering in plan.order_by:
        column = aliases[ordering.key]
        statement = statement.order_by(
            column.desc().nulls_last()
            if ordering.direction == "desc"
            else column.asc().nulls_last()
        )

    statement = statement.limit(plan.limit)
    raw_rows = session.execute(statement).mappings().all()

    currency_by_column: dict[str, str] = {}
    columns: list[AskResultColumn] = []
    for item, _ in compiled:
        columns.append(AskResultColumn(key=item.alias, label=item.label, format=item.format))
        if item.format == "currency":
            currency = _currency_code(item.expression)
            if currency is None:
                raise InvalidPlanError(
                    f"Currency column {item.alias} must use salary_usd or a currency expression"
                )
            currency_by_column[item.alias] = currency

    rows: list[dict[str, str | int | None]] = []
    for row in raw_rows:
        rows.append(
            {item.alias: _serialize_cell(row[item.alias], item.format) for item, _ in compiled}
        )

    scalar = (
        len(rows) == 1
        and len(columns) == 1
        and any(_has_aggregate(item.expression) for item, _ in compiled)
        and not plan.group_by
    )
    return AskResult(
        kind="scalar" if scalar else "table",
        currency_by_column=currency_by_column,
        columns=columns,
        rows=rows,
    )


def _interpretation(plan: QueryPlan) -> str:
    selected = ", ".join(item.label for item in plan.select)
    parts = [selected]
    if plan.group_by:
        parts.append("grouped by " + ", ".join(field.replace("_", " ") for field in plan.group_by))
    if plan.where:
        parts.append("with requested filters")
    if plan.order_by:
        parts.append("ordered by " + ", ".join(order.key for order in plan.order_by))
    if plan.limit:
        parts.append(f"limited to {plan.limit} row(s)")
    return "; ".join(parts)


def _answer_text(result: AskResult) -> str:
    if not result.rows:
        return "No rows matched the available data."
    if result.kind == "scalar":
        column = result.columns[0]
        value = result.rows[0].get(column.key)
        if value is None:
            return f"{column.label}: no value is available."
        currency = result.currency_by_column.get(column.key)
        if column.format == "currency" and currency:
            return f"{column.label}: {currency} {value}."
        if column.format == "percent":
            return f"{column.label}: {value}%."
        return f"{column.label}: {value}."
    return f"Found {len(result.rows):,} row(s) from Compensation Hub data."


def ask(
    session: Session,
    question: str,
    planner: QueryPlanner,
    history: list[AskHistoryItem] | None = None,
) -> AskOutcome:
    """Answer from stored data when possible; otherwise explain the missing data."""
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
                f"{UNSUPPORTED_PREFIX} The question could not be mapped to a valid read-only "
                "data query."
            ),
        )

    if response.status == "unsupported":
        return AskOutcome(
            status="unsupported",
            answer=f"{UNSUPPORTED_PREFIX} Missing data: {response.missing}",
        )

    try:
        result = _execute_plan(session, response.plan)
    except InvalidPlanError as error:
        logger.warning("Rejected Ask Compensation plan: %s", error)
        return AskOutcome(
            status="unsupported",
            answer=f"{UNSUPPORTED_PREFIX} {error}",
        )

    return AskOutcome(
        status="answered",
        answer=_answer_text(result),
        interpretation=_interpretation(response.plan),
        plan=response.plan,
        result=result,
    )
