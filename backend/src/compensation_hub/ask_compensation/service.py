import json
import logging
from dataclasses import dataclass
from typing import Literal

from pydantic import TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from compensation_hub.ask_compensation.executor import InvalidProgramError, execute_program
from compensation_hub.ask_compensation.provider import PlannerContext, PlannerTurn, QueryPlanner
from compensation_hub.ask_compensation.schemas import (
    AskHistoryItem,
    AskResult,
    PlannerResponse,
    QueryProgram,
)
from compensation_hub.db.models import Compensation, Employee, FxRate
from compensation_hub.employees.service import list_filter_options

logger = logging.getLogger(__name__)

PLANNER_RESPONSE = TypeAdapter[PlannerResponse](PlannerResponse)
UNSUPPORTED_PREFIX = "I can't answer that from the data available in Compensation Hub."


@dataclass(frozen=True)
class AskOutcome:
    status: Literal["answered", "unsupported"]
    answer: str
    interpretation: str | None = None
    plan: QueryProgram | None = None
    result: AskResult | None = None
    analytics_path: str | None = None


class InvalidPlannerResponseError(Exception):
    """The model response could not be validated into the read-only query language."""


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
        raise InvalidPlannerResponseError(
            f"Planner response is not valid JSON: {error.msg}"
        ) from error

    try:
        return PLANNER_RESPONSE.validate_python(_drop_nulls(payload))
    except ValidationError as error:
        raise InvalidPlannerResponseError(
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
            plan_json=json.dumps(
                item.plan.model_dump(mode="json"),
                separators=(",", ":"),
            ),
        )
        for item in history
    )


def ask(
    session: Session,
    question: str,
    planner: QueryPlanner,
    history: list[AskHistoryItem] | None = None,
) -> AskOutcome:
    """Plan and derive one read-only answer from available Compensation Hub data."""
    context = _planner_context(session)
    raw = planner.plan(question, context, _planner_history(history or []))

    try:
        response = parse_planner_response(raw)
    except InvalidPlannerResponseError as error:
        logger.warning("Rejected Ask Compensation planner response: %s", error)
        return AskOutcome(
            status="unsupported",
            answer=(
                f"{UNSUPPORTED_PREFIX} The question could not be mapped to a valid read-only query."
            ),
        )

    if response.status == "unsupported":
        return AskOutcome(
            status="unsupported",
            answer=f"{UNSUPPORTED_PREFIX} {response.reason}",
        )

    try:
        executed = execute_program(session, response.plan, context)
    except InvalidProgramError as error:
        logger.warning("Rejected Ask Compensation query program: %s", error)
        return AskOutcome(
            status="unsupported",
            answer=f"{UNSUPPORTED_PREFIX} {error}",
        )

    return AskOutcome(
        status="answered",
        answer=executed.answer,
        interpretation=executed.interpretation,
        plan=response.plan,
        result=executed.result,
        analytics_path=executed.analytics_path,
    )
