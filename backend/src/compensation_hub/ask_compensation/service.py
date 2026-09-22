import json
import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from pydantic import TypeAdapter, ValidationError
from sqlalchemy.orm import Session

from compensation_hub.analytics.service import (
    ANALYTICS_CURRENCY,
    AnalyticsFilters,
    BreakdownRow,
    SortBy,
    get_breakdown,
    get_summary,
)
from compensation_hub.ask_compensation.provider import PlannerContext, QueryPlanner
from compensation_hub.ask_compensation.schemas import Metric, PlannerResponse, QueryPlan
from compensation_hub.employees.service import list_filter_options

logger = logging.getLogger(__name__)

PLANNER_RESPONSE = TypeAdapter[PlannerResponse](PlannerResponse)

METRIC_LABELS: dict[Metric, str] = {
    "employee_count": "Employee count",
    "average_salary": "Average annual salary",
    "total_payroll": "Total annual payroll",
}
METRIC_SORT_COLUMNS: dict[Metric, SortBy] = {
    "employee_count": "employee_count",
    "average_salary": "average_salary_usd",
    "total_payroll": "total_payroll_usd",
}
DIMENSION_LABELS = {"country": "country", "department": "department", "job_title": "job title"}
UNSUPPORTED_ANSWER = (
    "This question cannot be answered reliably with the supported compensation analytics. "
    "Try asking about employee count, average annual salary, or total annual payroll, "
    "optionally filtered or grouped by country, department, or job title."
)
NORMALIZATION_NOTE = (
    f"Monetary values are normalized to {ANALYTICS_CURRENCY} using seeded exchange rates."
)


class InvalidPlanError(Exception):
    """The provider's response could not be validated into a supported query plan."""


@dataclass(frozen=True)
class AskOutcome:
    status: Literal["answered", "unsupported"]
    answer: str
    plan: QueryPlan | None = None
    rows: tuple[BreakdownRow, ...] = ()


def parse_planner_response(raw: str) -> PlannerResponse:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        raise InvalidPlanError(f"Planner response is not valid JSON: {error.msg}") from error
    try:
        return PLANNER_RESPONSE.validate_python(payload)
    except ValidationError as error:
        raise InvalidPlanError(
            f"Planner response failed validation: {error.error_count()} errors"
        ) from error


def _validate_filter_values(plan: QueryPlan, context: PlannerContext) -> str | None:
    """Return a reason when a filter names a value that does not exist in the data."""
    known = {
        "country": set(context.countries),
        "department": set(context.departments),
        "job_title": set(context.job_titles),
    }
    for field, values in known.items():
        value = getattr(plan.filters, field)
        if value is not None and value not in values:
            return f"There is no {DIMENSION_LABELS[field]} named {value!r} in the employee data."
    return None


def _describe_filters(plan: QueryPlan) -> str:
    parts = [
        f"{DIMENSION_LABELS[field]} {value}"
        for field, value in (
            ("country", plan.filters.country),
            ("department", plan.filters.department),
            ("job_title", plan.filters.job_title),
        )
        if value is not None
    ]
    return f" for {', '.join(parts)}" if parts else " across the organization"


def _metric_value(metric: Metric, row: BreakdownRow) -> str:
    if metric == "employee_count":
        return f"{row.employee_count:,}"
    value: Decimal | None = (
        row.total_payroll_usd if metric == "total_payroll" else row.average_salary_usd
    )
    return "not available" if value is None else f"{ANALYTICS_CURRENCY} {value:,.2f}"


def _compose_answer(plan: QueryPlan, rows: list[BreakdownRow]) -> str:
    label = METRIC_LABELS[plan.metric]
    scope = _describe_filters(plan)
    monetary = plan.metric != "employee_count"

    if plan.group_by is None:
        row = rows[0]
        sentence = f"{label}{scope}: {_metric_value(plan.metric, row)}"
        if monetary:
            sentence += f" ({row.employee_count:,} employees)"
        sentence += "."
    elif not rows:
        sentence = f"No employees match{scope}."
    else:
        dimension = DIMENSION_LABELS[plan.group_by]
        qualifier = ""
        if plan.sort is not None:
            direction = "highest" if plan.sort == "desc" else "lowest"
            qualifier = f", {direction} first"
        if plan.limit is not None:
            qualifier += f", top {plan.limit}"
        listing = "; ".join(f"{row.key}: {_metric_value(plan.metric, row)}" for row in rows)
        sentence = f"{label} by {dimension}{scope}{qualifier}: {listing}."

    return f"{sentence} {NORMALIZATION_NOTE}" if monetary else sentence


def _execute(session: Session, plan: QueryPlan) -> list[BreakdownRow]:
    filters = AnalyticsFilters(
        country=plan.filters.country,
        department=plan.filters.department,
        job_title=plan.filters.job_title,
    )
    if plan.group_by is None:
        summary = get_summary(session, filters)
        return [
            BreakdownRow(
                key="",
                employee_count=summary.employee_count,
                total_payroll_usd=summary.total_payroll_usd,
                average_salary_usd=summary.average_salary_usd,
            )
        ]
    return get_breakdown(
        session,
        plan.group_by,
        filters,
        sort_by=METRIC_SORT_COLUMNS[plan.metric] if plan.sort else "key",
        descending=plan.sort == "desc",
        limit=plan.limit,
    )


def ask(session: Session, question: str, planner: QueryPlanner) -> AskOutcome:
    """Interpret the question with the planner, then answer it from deterministic analytics.

    Provider failures propagate as PlannerUnavailableError so the API can report the feature
    as unavailable; invalid or unsupported plans produce an explicit unsupported outcome.
    """
    options = list_filter_options(session)
    context = PlannerContext(
        countries=options.countries,
        departments=options.departments,
        job_titles=options.job_titles,
    )

    raw = planner.plan(question, context)
    try:
        response = parse_planner_response(raw)
    except InvalidPlanError as error:
        logger.warning("Rejected planner response: %s", error)
        return AskOutcome(status="unsupported", answer=UNSUPPORTED_ANSWER)

    if response.status == "unsupported":
        return AskOutcome(status="unsupported", answer=f"{UNSUPPORTED_ANSWER} ({response.reason})")

    plan = response.plan
    reason = _validate_filter_values(plan, context)
    if reason is not None:
        return AskOutcome(status="unsupported", answer=f"{reason} {UNSUPPORTED_ANSWER}")

    rows = _execute(session, plan)
    return AskOutcome(
        status="answered", answer=_compose_answer(plan, rows), plan=plan, rows=tuple(rows)
    )
