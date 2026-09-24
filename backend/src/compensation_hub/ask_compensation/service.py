import json
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from pydantic import TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from compensation_hub.ask_compensation.answers import (
    analytics_view,
    compose_answer,
    is_scalar,
    primary_column,
)
from compensation_hub.ask_compensation.execution import (
    QueryResult,
    begin_read_only,
    ensure_fx_rates,
    execute_sql,
)
from compensation_hub.ask_compensation.plan import PlannerResponse, QueryResponse
from compensation_hub.ask_compensation.provider import (
    Correction,
    PlannerContext,
    PlannerTurn,
    QueryPlanner,
)
from compensation_hub.ask_compensation.sql_validation import (
    ForbiddenSqlError,
    InvalidSqlError,
    UnknownReferenceError,
    ValidatedSql,
    validate_sql,
)
from compensation_hub.ask_compensation.surface import (
    STORED_DATA_DESCRIPTION,
    VOCABULARY_COLUMNS,
    vocabulary_query,
)
from compensation_hub.db.models import FxRate

logger = logging.getLogger(__name__)

PLANNER_RESPONSE = TypeAdapter[PlannerResponse](PlannerResponse)

# The planner gets one chance to correct a response the application rejected; a second
# rejection is reported to the HR Manager instead of retrying indefinitely.
MAX_ATTEMPTS = 2

UNINTERPRETABLE_ANSWER = (
    "This question could not be turned into a reliable query over the employee and "
    "compensation data. Try rephrasing it."
)
READ_ONLY_ANSWER = (
    "Ask Compensation only answers read-only questions about the employee and compensation "
    "data, so this request cannot be run."
)
# The planner's own reason is logged, not shown: wording stays consistent and never describes
# the query machinery.
OUT_OF_SCOPE_ANSWER = (
    "Ask Compensation answers factual, read-only questions about employees and their current "
    "compensation. It does not change data, recommend pay, judge performance, or answer "
    "unrelated questions."
)
TIMEOUT_ANSWER = "This question needs a query that takes too long to run. Try narrowing it."
# A correlated subquery re-reads the surface once per employee; on 10,000 employees that runs
# for tens of seconds, while the same comparison with a window function takes milliseconds.
SLOW_QUERY_PROBLEM = (
    "The query exceeded the time limit. Avoid correlated subqueries: compare rows with their "
    "group's figures using window functions such as AVG(salary_usd) OVER (PARTITION BY "
    "department), or join a CTE grouped once."
)
# PostgreSQL error classes a corrected query can fix: syntax or access rule violations,
# data exceptions, and cardinality violations such as a scalar subquery returning many rows.
CORRECTABLE_SQLSTATE_CLASSES = ("42", "22", "21")
# Within those classes, a missing privilege or table means the surface itself is broken, which
# no rewrite of the query can fix, so these are raised as server errors instead.
INFRASTRUCTURE_SQLSTATES = frozenset({"42501", "42P01"})
READ_ONLY_VIOLATION = "25006"
QUERY_CANCELED = "57014"
CONTEXT_TIMEOUT = "5s"


class InvalidPlanError(Exception):
    """The provider's response could not be validated into a planner response."""


@dataclass(frozen=True)
class DataContext:
    vocabulary: dict[str, tuple[str, ...]]
    fx_rates: dict[str, Decimal]


@dataclass(frozen=True)
class AskOutcome:
    status: Literal["answered", "missing_data", "unsupported"]
    answer: str
    missing: tuple[str, ...] = ()
    sql: str | None = None
    currency: str = "USD"
    interpretation: str | None = None
    result: QueryResult | None = None
    scalar: bool = False
    primary: str | None = None
    analytics_view: dict[str, str | None] | None = None


def _drop_nulls(value: object) -> object:
    # Schema-guided providers emit every declared property, so a query arrives with
    # "reason": null, "missing": [], and so on. Empty values carry no content; unexpected
    # keys with content are still rejected by the strict models.
    if isinstance(value, dict):
        return {
            key: _drop_nulls(item) for key, item in value.items() if item is not None and item != []
        }
    return value


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
        return PLANNER_RESPONSE.validate_python(_drop_nulls(payload))
    except ValidationError as error:
        raise InvalidPlanError(
            f"Planner response failed validation: {error.error_count()} errors"
        ) from error


def load_data_context(session: Session) -> DataContext:
    vocabulary: dict[str, tuple[str, ...]] = {}
    connection = session.connection()
    for name in VOCABULARY_COLUMNS:
        values = connection.exec_driver_sql(vocabulary_query(name)).scalars()
        vocabulary[name] = tuple(str(value) for value in values)
    rates = session.execute(select(FxRate.currency_code, FxRate.rate_to_usd)).all()
    return DataContext(vocabulary=vocabulary, fx_rates={code: rate for code, rate in rates})


def _missing(names: Sequence[str]) -> AskOutcome:
    described = [name.replace("_", " ") for name in names]
    return AskOutcome(
        status="missing_data",
        answer=(
            f"This needs data Compensation Hub does not store: {', '.join(described)}. "
            f"{STORED_DATA_DESCRIPTION}."
        ),
        missing=tuple(described),
    )


def _run(
    session: Session, response: QueryResponse, validated: ValidatedSql, rate: Decimal
) -> AskOutcome:
    begin_read_only(session)
    try:
        result = execute_sql(session, validated, response.currency, rate)
    finally:
        session.rollback()
    primary = primary_column(result, response.primary)
    return AskOutcome(
        status="answered",
        answer=compose_answer(result, primary, response.currency),
        sql=validated.sql,
        currency=response.currency,
        interpretation=response.interpretation,
        result=result,
        scalar=is_scalar(result),
        primary=primary,
        analytics_view=analytics_view(validated.tree, response.currency),
    )


def ask(
    session: Session, question: str, history: Sequence[PlannerTurn], planner: QueryPlanner
) -> AskOutcome:
    """Interpret the question with the planner, then answer it from PostgreSQL.

    Provider failures propagate as PlannerUnavailableError so the API can report the feature
    as unavailable. Questions that need data the product does not store produce a missing-data
    outcome; requests that are not read-only questions about the data are unsupported.
    """
    # Reading the vocabulary runs fixed application queries, not planned SQL.
    begin_read_only(session, CONTEXT_TIMEOUT)
    ensure_fx_rates(session)
    context = load_data_context(session)
    # No transaction is held open while the provider is called.
    session.rollback()

    planner_context = PlannerContext(
        vocabulary=context.vocabulary, currencies=tuple(sorted(context.fx_rates))
    )
    correction: Correction | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        final = attempt == MAX_ATTEMPTS
        raw = planner.plan(question, history, planner_context, correction)
        try:
            response = parse_planner_response(raw)
        except InvalidPlanError as error:
            logger.warning("Rejected planner response: %s", error)
            if final:
                return AskOutcome(status="unsupported", answer=UNINTERPRETABLE_ANSWER)
            correction = Correction(raw, "It was not a valid response object.")
            continue

        if response.status == "unsupported":
            logger.info("Planner declined the question: %s", response.reason)
            return AskOutcome(status="unsupported", answer=OUT_OF_SCOPE_ANSWER)
        if response.status == "missing_data":
            return _missing(response.missing)

        rate = context.fx_rates.get(response.currency)
        if rate is None:
            return _missing([f"{response.currency} exchange rate"])
        try:
            validated = validate_sql(response.sql, frozenset(response.percent_columns))
        except ForbiddenSqlError as error:
            logger.warning("Rejected forbidden SQL: %s", error.message)
            return AskOutcome(status="unsupported", answer=READ_ONLY_ANSWER)
        except UnknownReferenceError as error:
            if final:
                return _missing(error.names)
            correction = Correction(raw, error.message)
            continue
        except InvalidSqlError as error:
            logger.info("Rejected planned SQL: %s", error.message)
            if final:
                return AskOutcome(status="unsupported", answer=UNINTERPRETABLE_ANSWER)
            correction = Correction(raw, error.message)
            continue

        try:
            return _run(session, response, validated, rate)
        except DBAPIError as error:
            sqlstate = str(getattr(error.orig, "sqlstate", "") or "")
            if sqlstate == QUERY_CANCELED:
                if final:
                    return AskOutcome(status="unsupported", answer=TIMEOUT_ANSWER)
                correction = Correction(raw, SLOW_QUERY_PROBLEM)
                continue
            if sqlstate == READ_ONLY_VIOLATION:
                # Validation should make this unreachable; PostgreSQL refusing is the backstop.
                logger.error("PostgreSQL refused a write from validated SQL")
                return AskOutcome(status="unsupported", answer=READ_ONLY_ANSWER)
            correctable = sqlstate.startswith(CORRECTABLE_SQLSTATE_CLASSES)
            if not correctable or sqlstate in INFRASTRUCTURE_SQLSTATES:
                raise
            diagnostic = getattr(error.orig, "diag", None)
            message = getattr(diagnostic, "message_primary", None) or "The query failed."
            logger.info("Planned SQL failed in PostgreSQL: %s", message)
            if final:
                return AskOutcome(status="unsupported", answer=UNINTERPRETABLE_ANSWER)
            correction = Correction(raw, f"PostgreSQL rejected the query: {message}")

    return AskOutcome(status="unsupported", answer=UNINTERPRETABLE_ANSWER)
