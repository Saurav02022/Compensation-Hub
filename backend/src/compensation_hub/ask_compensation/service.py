import json
import logging
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Literal
from urllib.parse import urlencode

from pydantic import TypeAdapter, ValidationError
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from compensation_hub.analytics.service import SALARY_USD
from compensation_hub.ask_compensation.provider import PlannerContext, PlannerTurn, QueryPlanner
from compensation_hub.ask_compensation.schemas import (
    AskHistoryItem,
    AskResult,
    AskResultColumn,
    Metric,
    PlannerResponse,
    QueryFilters,
    QueryPlan,
)
from compensation_hub.db.models import Compensation, Employee, FxRate
from compensation_hub.employees.service import list_filter_options

logger = logging.getLogger(__name__)

PLANNER_RESPONSE = TypeAdapter[PlannerResponse](PlannerResponse)
CENTS = Decimal("0.01")
PERCENT = Decimal("0.01")
MONETARY_METRICS: set[Metric] = {
    "average_salary",
    "total_payroll",
    "minimum_salary",
    "maximum_salary",
    "median_salary",
}
METRIC_LABELS: dict[Metric, str] = {
    "employee_count": "Employee count",
    "average_salary": "Average annual salary",
    "total_payroll": "Total annual payroll",
    "minimum_salary": "Minimum annual salary",
    "maximum_salary": "Maximum annual salary",
    "median_salary": "Median annual salary",
}
DIMENSION_LABELS = {
    "country": "country",
    "department": "department",
    "job_title": "job title",
    "currency_code": "currency",
}
GROUP_COLUMNS = {
    "country": Employee.country,
    "department": Employee.department,
    "job_title": Employee.job_title,
    "currency_code": Compensation.currency_code,
}
UNSUPPORTED_PREFIX = "I can't answer that from the data available in Compensation Hub."


class InvalidPlanError(Exception):
    """The provider response could not be validated into a supported read-only query plan."""


@dataclass(frozen=True)
class AskOutcome:
    status: Literal["answered", "unsupported"]
    answer: str
    interpretation: str | None = None
    plan: QueryPlan | None = None
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


def _plan_filters(plan: QueryPlan) -> list[QueryFilters]:
    values = [plan.filters]
    if plan.denominator_filters is not None:
        values.append(plan.denominator_filters)
    if plan.compare_filters is not None:
        values.append(plan.compare_filters)
    return values


def _validate_plan_values(plan: QueryPlan, context: PlannerContext) -> str | None:
    known = {
        "country": set(context.countries),
        "department": set(context.departments),
        "job title": set(context.job_titles),
        "currency": set(context.currency_codes),
    }
    for filters in _plan_filters(plan):
        checks = (
            ("country", filters.countries, known["country"]),
            ("department", filters.departments, known["department"]),
            ("job title", filters.job_titles, known["job title"]),
            ("currency", filters.currency_codes, known["currency"]),
        )
        for label, values, allowed in checks:
            unknown = sorted({value for value in values if value not in allowed})
            if unknown:
                return f"No {label} value exists in the data for: {', '.join(unknown)}."
    if plan.target_currency is not None and plan.target_currency not in known["currency"]:
        return f"No exchange rate is configured for {plan.target_currency}."
    return None


def _base_select(*columns: Any) -> Select[Any]:
    return (
        select(*columns)
        .select_from(Employee)
        .outerjoin(Compensation, Compensation.employee_id == Employee.id)
        .outerjoin(FxRate, FxRate.currency_code == Compensation.currency_code)
    )


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _apply_filters(statement: Select[Any], filters: QueryFilters) -> Select[Any]:
    if filters.countries:
        statement = statement.where(Employee.country.in_(filters.countries))
    if filters.departments:
        statement = statement.where(Employee.department.in_(filters.departments))
    if filters.job_titles:
        statement = statement.where(Employee.job_title.in_(filters.job_titles))
    if filters.currency_codes:
        statement = statement.where(Compensation.currency_code.in_(filters.currency_codes))
    if filters.employee_code is not None:
        statement = statement.where(Employee.employee_code == filters.employee_code)
    if filters.name_contains is not None:
        pattern = f"%{_escape_like(filters.name_contains)}%"
        statement = statement.where(Employee.full_name.ilike(pattern, escape="\\"))
    if filters.salary_usd_min is not None:
        statement = statement.where(SALARY_USD >= filters.salary_usd_min)
    if filters.salary_usd_max is not None:
        statement = statement.where(SALARY_USD <= filters.salary_usd_max)
    if filters.has_compensation is True:
        statement = statement.where(Compensation.employee_id.is_not(None))
    elif filters.has_compensation is False:
        statement = statement.where(Compensation.employee_id.is_(None))
    return statement


def _metric_expression(metric: Metric) -> Any:
    if metric == "employee_count":
        return func.count(Employee.id)
    if metric == "total_payroll":
        return func.coalesce(func.sum(SALARY_USD), 0)
    if metric == "average_salary":
        return func.avg(SALARY_USD)
    if metric == "minimum_salary":
        return func.min(SALARY_USD)
    if metric == "maximum_salary":
        return func.max(SALARY_USD)
    return func.percentile_cont(0.5).within_group(SALARY_USD)


def _money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(CENTS, rounding=ROUND_HALF_UP)


def _metric_scalar(session: Session, metric: Metric, filters: QueryFilters) -> Decimal | None:
    value = session.execute(
        _apply_filters(_base_select(_metric_expression(metric).label("value")), filters)
    ).scalar_one()
    if metric == "employee_count":
        return Decimal(int(value))
    return None if value is None else _money(value)


def _currency_rate(session: Session, currency_code: str) -> Decimal:
    value = session.scalar(
        select(FxRate.rate_to_usd).where(FxRate.currency_code == currency_code)
    )
    if value is None:
        raise InvalidPlanError(f"No exchange rate is configured for {currency_code}")
    return Decimal(value)


def _converted(value_usd: Decimal, rate_to_usd: Decimal) -> Decimal:
    return (value_usd / rate_to_usd).quantize(CENTS, rounding=ROUND_HALF_UP)


def _metric_currency(session: Session, plan: QueryPlan) -> tuple[str | None, Decimal]:
    if plan.metric not in MONETARY_METRICS:
        return None, Decimal("1")
    currency = plan.target_currency or "USD"
    return currency, _currency_rate(session, currency)


def _format_metric(metric: Metric, value: Decimal | None, currency: str | None) -> str:
    if value is None:
        return "not available"
    if metric == "employee_count":
        return f"{int(value):,}"
    assert currency is not None
    return f"{currency} {value:,.2f}"


def _row_value(metric: Metric, value: Decimal | None) -> str | int | None:
    if value is None:
        return None
    if metric == "employee_count":
        return int(value)
    return f"{value:.2f}"


def _list_phrase(values: list[str]) -> str:
    if len(values) == 1:
        return values[0]
    return ", ".join(values[:-1]) + f" or {values[-1]}"


def _describe_filters(filters: QueryFilters) -> str:
    parts: list[str] = []
    if filters.countries:
        parts.append(f"country {_list_phrase(filters.countries)}")
    if filters.departments:
        parts.append(f"department {_list_phrase(filters.departments)}")
    if filters.job_titles:
        parts.append(f"job title {_list_phrase(filters.job_titles)}")
    if filters.currency_codes:
        parts.append(f"currency {_list_phrase(filters.currency_codes)}")
    if filters.employee_code is not None:
        parts.append(f"employee code {filters.employee_code}")
    if filters.name_contains is not None:
        parts.append(f'name containing "{filters.name_contains}"')
    if filters.salary_usd_min is not None:
        parts.append(f"normalized salary at least USD {filters.salary_usd_min:,.2f}")
    if filters.salary_usd_max is not None:
        parts.append(f"normalized salary at most USD {filters.salary_usd_max:,.2f}")
    if filters.has_compensation is True:
        parts.append("with current compensation")
    elif filters.has_compensation is False:
        parts.append("without current compensation")
    return ", ".join(parts) if parts else "the organization"


def _interpretation(plan: QueryPlan) -> str:
    if plan.kind == "aggregate":
        assert plan.metric is not None
        text = METRIC_LABELS[plan.metric]
        if plan.group_by is not None:
            text += f" by {DIMENSION_LABELS[plan.group_by]}"
        text += f" for {_describe_filters(plan.filters)}"
        if plan.target_currency is not None:
            text += f", converted to {plan.target_currency}"
        return text
    if plan.kind == "employees":
        text = f"Employees for {_describe_filters(plan.filters)}"
        if plan.sort_by is not None:
            text += f", sorted by {plan.sort_by.replace('_', ' ')}"
        if plan.limit is not None:
            text += f", first {plan.limit}"
        if plan.target_currency is not None:
            text += f", normalized salary in {plan.target_currency}"
        return text
    if plan.kind == "values":
        assert plan.field is not None
        return (
            f"Distinct {DIMENSION_LABELS[plan.field]} values for "
            f"{_describe_filters(plan.filters)}"
        )
    if plan.kind == "share":
        assert plan.metric is not None and plan.denominator_filters is not None
        return (
            f"{METRIC_LABELS[plan.metric]} share for {_describe_filters(plan.filters)} "
            f"within {_describe_filters(plan.denominator_filters)}"
        )
    assert plan.metric is not None
    assert plan.compare_filters is not None
    assert plan.comparison is not None
    return (
        f"{plan.comparison.replace('_', ' ')} in {METRIC_LABELS[plan.metric].lower()} between "
        f"{_describe_filters(plan.filters)} and {_describe_filters(plan.compare_filters)}"
    )


def _analytics_path(plan: QueryPlan) -> str | None:
    if plan.kind != "aggregate" or plan.metric not in (
        "employee_count",
        "average_salary",
        "total_payroll",
    ):
        return None
    if plan.group_by == "currency_code" or plan.target_currency not in (None, "USD"):
        return None
    filters = plan.filters
    if any(
        (
            filters.currency_codes,
            filters.employee_code is not None,
            filters.name_contains is not None,
            filters.salary_usd_min is not None,
            filters.salary_usd_max is not None,
            filters.has_compensation is not None,
        )
    ):
        return None
    if any(
        len(values) > 1
        for values in (filters.countries, filters.departments, filters.job_titles)
    ):
        return None
    params: dict[str, str] = {}
    if filters.countries:
        params["country"] = filters.countries[0]
    if filters.departments:
        params["department"] = filters.departments[0]
    if filters.job_titles:
        params["job_title"] = filters.job_titles[0]
    if plan.group_by is not None:
        params["by"] = plan.group_by
    params["metric"] = {
        "employee_count": "headcount",
        "average_salary": "average",
        "total_payroll": "payroll",
    }[plan.metric]
    return "/analytics?" + urlencode(params)


def _execute_aggregate(session: Session, plan: QueryPlan) -> AskOutcome:
    assert plan.metric is not None
    expression = _metric_expression(plan.metric).label("value")
    currency, rate = _metric_currency(session, plan)

    if plan.group_by is None:
        raw = session.execute(
            _apply_filters(_base_select(expression), plan.filters)
        ).scalar_one()
        value = Decimal(int(raw)) if plan.metric == "employee_count" else (
            None if raw is None else _money(raw)
        )
        if value is not None and plan.metric in MONETARY_METRICS:
            value = _converted(value, rate)
        result = AskResult(
            kind="scalar",
            currency=currency,
            columns=[
                AskResultColumn(
                    key="value",
                    label=METRIC_LABELS[plan.metric],
                    format="count" if plan.metric == "employee_count" else "currency",
                )
            ],
            rows=[{"value": _row_value(plan.metric, value)}],
        )
        answer = (
            f"{METRIC_LABELS[plan.metric]} for {_describe_filters(plan.filters)}: "
            f"{_format_metric(plan.metric, value, currency)}."
        )
    else:
        group_column = GROUP_COLUMNS[plan.group_by]
        statement = _apply_filters(
            _base_select(group_column.label("key"), expression), plan.filters
        ).group_by(group_column)
        if plan.sort is not None:
            ordering = (
                expression.desc().nulls_last()
                if plan.sort == "desc"
                else expression.asc().nulls_last()
            )
            statement = statement.order_by(ordering, group_column.asc())
        else:
            statement = statement.order_by(group_column.asc())
        if plan.limit is not None:
            statement = statement.limit(plan.limit)
        rows: list[dict[str, str | int | None]] = []
        for row in session.execute(statement):
            raw = row.value
            value = Decimal(int(raw)) if plan.metric == "employee_count" else (
                None if raw is None else _money(raw)
            )
            if value is not None and plan.metric in MONETARY_METRICS:
                value = _converted(value, rate)
            rows.append({"key": row.key, "value": _row_value(plan.metric, value)})
        result = AskResult(
            kind="table",
            currency=currency,
            columns=[
                AskResultColumn(key="key", label=DIMENSION_LABELS[plan.group_by].title()),
                AskResultColumn(
                    key="value",
                    label=METRIC_LABELS[plan.metric],
                    format="count" if plan.metric == "employee_count" else "currency",
                ),
            ],
            rows=rows,
        )
        answer = (
            f"{METRIC_LABELS[plan.metric]} by {DIMENSION_LABELS[plan.group_by]} for "
            f"{_describe_filters(plan.filters)}. {len(rows):,} result(s)."
        )

    return AskOutcome(
        status="answered",
        answer=answer,
        interpretation=_interpretation(plan),
        plan=plan,
        result=result,
        analytics_path=_analytics_path(plan),
    )


def _execute_employees(session: Session, plan: QueryPlan) -> AskOutcome:
    total = int(
        session.execute(
            _apply_filters(_base_select(func.count(Employee.id)), plan.filters)
        ).scalar_one()
    )
    limit = plan.limit or 10
    currency = plan.target_currency or "USD"
    rate = _currency_rate(session, currency)

    statement = _apply_filters(
        _base_select(
            Employee.full_name.label("full_name"),
            Employee.employee_code.label("employee_code"),
            Employee.country.label("country"),
            Employee.department.label("department"),
            Employee.job_title.label("job_title"),
            Compensation.annual_salary.label("annual_salary"),
            Compensation.currency_code.label("currency_code"),
            SALARY_USD.label("salary_usd"),
        ),
        plan.filters,
    )
    sort_by = plan.sort_by or "full_name"
    sort_column = {
        "full_name": Employee.full_name,
        "employee_code": Employee.employee_code,
        "salary_usd": SALARY_USD,
        "annual_salary": Compensation.annual_salary,
    }[sort_by]
    ordering = (
        sort_column.desc().nulls_last()
        if plan.sort == "desc"
        else sort_column.asc().nulls_last()
    )
    statement = statement.order_by(
        ordering, Employee.full_name.asc(), Employee.employee_code.asc()
    ).limit(limit)

    rows: list[dict[str, str | int | None]] = []
    for row in session.execute(statement):
        local_salary = None if row.annual_salary is None else _money(row.annual_salary)
        salary_target = (
            None
            if row.salary_usd is None
            else _converted(_money(row.salary_usd), rate)
        )
        local_compensation = (
            "Not set"
            if local_salary is None or row.currency_code is None
            else f"{row.currency_code} {local_salary:,.2f}"
        )
        rows.append(
            {
                "employee": row.full_name,
                "employee_code": row.employee_code,
                "role": f"{row.job_title} · {row.department}",
                "country": row.country,
                "local_compensation": local_compensation,
                "salary": None if salary_target is None else f"{salary_target:.2f}",
            }
        )

    result = AskResult(
        kind="employees",
        currency=currency,
        columns=[
            AskResultColumn(key="employee", label="Employee"),
            AskResultColumn(key="employee_code", label="Employee code"),
            AskResultColumn(key="role", label="Role"),
            AskResultColumn(key="country", label="Country"),
            AskResultColumn(key="local_compensation", label="Local compensation"),
            AskResultColumn(key="salary", label=f"Salary in {currency}", format="currency"),
        ],
        rows=rows,
    )
    answer = (
        f"No employees match {_describe_filters(plan.filters)}."
        if total == 0
        else f"Found {total:,} matching employee(s). Showing {len(rows):,}."
    )
    return AskOutcome(
        status="answered",
        answer=answer,
        interpretation=_interpretation(plan),
        plan=plan,
        result=result,
    )


def _execute_values(session: Session, plan: QueryPlan) -> AskOutcome:
    assert plan.field is not None
    column = GROUP_COLUMNS[plan.field]
    statement = _apply_filters(
        _base_select(column.label("value")), plan.filters
    ).distinct()
    statement = statement.order_by(column.desc() if plan.sort == "desc" else column.asc())
    if plan.limit is not None:
        statement = statement.limit(plan.limit)
    values = [row.value for row in session.execute(statement) if row.value is not None]
    result = AskResult(
        kind="table",
        columns=[AskResultColumn(key="value", label=DIMENSION_LABELS[plan.field].title())],
        rows=[{"value": value} for value in values],
    )
    answer = (
        f"Found {len(values):,} distinct {DIMENSION_LABELS[plan.field]} value(s) for "
        f"{_describe_filters(plan.filters)}."
    )
    return AskOutcome(
        status="answered",
        answer=answer,
        interpretation=_interpretation(plan),
        plan=plan,
        result=result,
    )


def _execute_share(session: Session, plan: QueryPlan) -> AskOutcome:
    assert plan.metric is not None and plan.denominator_filters is not None
    numerator = _metric_scalar(session, plan.metric, plan.filters)
    denominator = _metric_scalar(session, plan.metric, plan.denominator_filters)
    if numerator is None or denominator is None or denominator == 0:
        return AskOutcome(
            status="unsupported",
            answer=f"{UNSUPPORTED_PREFIX} The comparison base has no value to divide by.",
        )
    if numerator > denominator:
        return AskOutcome(
            status="unsupported",
            answer=f"{UNSUPPORTED_PREFIX} The percentage scopes are inconsistent.",
        )
    percentage = ((numerator / denominator) * 100).quantize(PERCENT, rounding=ROUND_HALF_UP)
    result = AskResult(
        kind="scalar",
        columns=[AskResultColumn(key="value", label="Share", format="percent")],
        rows=[{"value": f"{percentage:.2f}"}],
    )
    answer = (
        f"{METRIC_LABELS[plan.metric]} for {_describe_filters(plan.filters)} is "
        f"{percentage:.2f}% of {_describe_filters(plan.denominator_filters)}."
    )
    return AskOutcome(
        status="answered",
        answer=answer,
        interpretation=_interpretation(plan),
        plan=plan,
        result=result,
    )


def _execute_compare(session: Session, plan: QueryPlan) -> AskOutcome:
    assert plan.metric is not None
    assert plan.compare_filters is not None
    assert plan.comparison is not None
    left = _metric_scalar(session, plan.metric, plan.filters)
    right = _metric_scalar(session, plan.metric, plan.compare_filters)
    if left is None or right is None:
        return AskOutcome(
            status="unsupported",
            answer=f"{UNSUPPORTED_PREFIX} One comparison scope has no compensation value.",
        )

    currency: str | None = None
    if plan.metric in MONETARY_METRICS:
        currency = plan.target_currency or "USD"
        rate = _currency_rate(session, currency)
        left = _converted(left, rate)
        right = _converted(right, rate)

    if plan.comparison == "difference":
        value = left - right
        if plan.metric == "employee_count":
            row_value: str | int | None = int(value)
            display = f"{int(value):,}"
            result_format = "count"
        else:
            row_value = f"{value:.2f}"
            display = f"{currency} {value:,.2f}"
            result_format = "currency"
    elif plan.comparison == "percent_difference":
        if right == 0:
            return AskOutcome(
                status="unsupported",
                answer=f"{UNSUPPORTED_PREFIX} The comparison value is zero.",
            )
        value = (((left - right) / abs(right)) * 100).quantize(
            PERCENT, rounding=ROUND_HALF_UP
        )
        row_value = f"{value:.2f}"
        display = f"{value:.2f}%"
        result_format = "percent"
        currency = None
    else:
        if right == 0:
            return AskOutcome(
                status="unsupported",
                answer=f"{UNSUPPORTED_PREFIX} The comparison value is zero.",
            )
        value = (left / right).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        row_value = f"{value:.2f}×"
        display = str(row_value)
        result_format = "text"
        currency = None

    result = AskResult(
        kind="scalar",
        currency=currency,
        columns=[AskResultColumn(key="value", label="Comparison", format=result_format)],
        rows=[{"value": row_value}],
    )
    answer = (
        f"{plan.comparison.replace('_', ' ').title()} in {METRIC_LABELS[plan.metric].lower()} "
        f"between {_describe_filters(plan.filters)} and {_describe_filters(plan.compare_filters)}: "
        f"{display}."
    )
    return AskOutcome(
        status="answered",
        answer=answer,
        interpretation=_interpretation(plan),
        plan=plan,
        result=result,
    )


def _execute(session: Session, plan: QueryPlan) -> AskOutcome:
    if plan.kind == "aggregate":
        return _execute_aggregate(session, plan)
    if plan.kind == "employees":
        return _execute_employees(session, plan)
    if plan.kind == "values":
        return _execute_values(session, plan)
    if plan.kind == "share":
        return _execute_share(session, plan)
    return _execute_compare(session, plan)


def ask(
    session: Session,
    question: str,
    planner: QueryPlanner,
    history: list[AskHistoryItem] | None = None,
) -> AskOutcome:
    """Plan one read-only question, validate it, then execute it against application data."""
    history = history or []
    context = _planner_context(session)
    raw = planner.plan(question, context, _planner_history(history))
    try:
        response = parse_planner_response(raw)
    except InvalidPlanError as error:
        logger.warning("Rejected planner response: %s", error)
        return AskOutcome(
            status="unsupported",
            answer=f"{UNSUPPORTED_PREFIX} The question could not be mapped to a safe data query.",
        )

    if response.status == "unsupported":
        return AskOutcome(
            status="unsupported",
            answer=f"{UNSUPPORTED_PREFIX} {response.reason}",
        )

    plan = response.plan
    reason = _validate_plan_values(plan, context)
    if reason is not None:
        return AskOutcome(status="unsupported", answer=f"{UNSUPPORTED_PREFIX} {reason}")

    try:
        return _execute(session, plan)
    except InvalidPlanError as error:
        logger.warning("Rejected executable plan: %s", error)
        return AskOutcome(status="unsupported", answer=f"{UNSUPPORTED_PREFIX} {error}")
