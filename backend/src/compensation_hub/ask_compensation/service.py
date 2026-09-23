import json
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from pydantic import TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from compensation_hub.ask_compensation.answers import (
    analytics_view,
    compose_answer,
    describe_query,
    primary_column,
)
from compensation_hub.ask_compensation.catalog import (
    FIELDS,
    STORED_DATA_DESCRIPTION,
    VOCABULARY_FIELDS,
)
from compensation_hub.ask_compensation.execution import (
    QueryResult,
    begin_read_only,
    ensure_fx_rates,
    execute_query,
)
from compensation_hub.ask_compensation.plan import PlannerResponse, Query
from compensation_hub.ask_compensation.provider import PlannerContext, PlannerTurn, QueryPlanner
from compensation_hub.ask_compensation.validation import (
    DataContext,
    InvalidQueryError,
    MissingDataError,
    ValidatedQuery,
    validate_query,
)
from compensation_hub.db.models import FxRate

logger = logging.getLogger(__name__)

PLANNER_RESPONSE = TypeAdapter[PlannerResponse](PlannerResponse)

UNINTERPRETABLE_ANSWER = (
    "This question could not be turned into a reliable query over the employee and "
    "compensation data. Try rephrasing it."
)


class InvalidPlanError(Exception):
    """The provider's response could not be validated into the query representation."""


@dataclass(frozen=True)
class AskOutcome:
    status: Literal["answered", "missing_data", "unsupported"]
    answer: str
    missing: tuple[str, ...] = ()
    query: Query | None = None
    validated: ValidatedQuery | None = None
    result: QueryResult | None = None
    interpretation: str | None = None
    primary: str | None = None
    analytics_view: dict[str, str | None] | None = None


def _drop_nulls(value: object) -> object:
    # Schema-guided providers emit every declared property, so a plan arrives with
    # "reason": null, conditions with "values": null, and so on. Nulls carry no content;
    # non-null unexpected keys are still rejected by the strict models.
    if isinstance(value, dict):
        return {key: _drop_nulls(item) for key, item in value.items() if item is not None}
    if isinstance(value, list):
        return [_drop_nulls(item) for item in value]
    return value


def parse_planner_response(raw: str) -> PlannerResponse:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    try:
        # Numbers become Decimal so thresholds and literals never pass through binary floats.
        payload = json.loads(text, parse_float=Decimal)
    except json.JSONDecodeError as error:
        raise InvalidPlanError(f"Planner response is not valid JSON: {error.msg}") from error
    try:
        return PLANNER_RESPONSE.validate_python(_drop_nulls(payload))
    except ValidationError as error:
        raise InvalidPlanError(
            f"Planner response failed validation: {error.error_count()} errors"
        ) from error


def load_data_context(session: Session) -> DataContext:
    vocabulary = {}
    for name in VOCABULARY_FIELDS:
        column = FIELDS[name].expression
        vocabulary[name] = tuple(
            session.scalars(
                select(column).where(column.is_not(None)).distinct().order_by(column)
            ).all()
        )
    rates = session.execute(select(FxRate.currency_code, FxRate.rate_to_usd)).all()
    return DataContext(vocabulary=vocabulary, fx_rates={code: rate for code, rate in rates})


def _missing(missing: Sequence[str], detail: str) -> AskOutcome:
    return AskOutcome(status="missing_data", answer=detail, missing=tuple(missing))


def ask(
    session: Session, question: str, history: Sequence[PlannerTurn], planner: QueryPlanner
) -> AskOutcome:
    """Interpret the question with the planner, then answer it from PostgreSQL.

    Provider failures propagate as PlannerUnavailableError so the API can report the feature
    as unavailable. Questions that need data the product does not store produce a missing-data
    outcome; plans that cannot be validated produce an unsupported outcome.
    """
    begin_read_only(session)
    ensure_fx_rates(session)
    context = load_data_context(session)
    # No transaction is held open while the provider is called.
    session.rollback()

    planner_context = PlannerContext(
        vocabulary=context.vocabulary, currencies=tuple(sorted(context.fx_rates))
    )
    raw = planner.plan(question, history, planner_context)
    try:
        response = parse_planner_response(raw)
    except InvalidPlanError as error:
        logger.warning("Rejected planner response: %s", error)
        return AskOutcome(status="unsupported", answer=UNINTERPRETABLE_ANSWER)

    if response.status == "unsupported":
        return AskOutcome(status="unsupported", answer=response.reason)
    if response.status == "missing_data":
        # The model sometimes names missing data like a field ("hire_date"); show plain words.
        described = [item.replace("_", " ") for item in response.missing]
        detail = (
            f"This needs data Compensation Hub does not store: {', '.join(described)}. "
            f"{STORED_DATA_DESCRIPTION}."
        )
        return _missing(described, detail)

    query = response.query
    try:
        validated = validate_query(query, context)
    except MissingDataError as error:
        return _missing(error.missing, error.message)
    except InvalidQueryError as error:
        logger.info("Rejected planned query: %s", error.message)
        return AskOutcome(
            status="unsupported",
            answer=f"{UNINTERPRETABLE_ANSWER} ({error.message})",
        )

    begin_read_only(session)
    try:
        result = execute_query(session, validated)
    finally:
        session.rollback()

    return AskOutcome(
        status="answered",
        answer=compose_answer(validated, result),
        query=query,
        validated=validated,
        result=result,
        interpretation=describe_query(validated),
        primary=primary_column(validated),
        analytics_view=analytics_view(validated),
    )
