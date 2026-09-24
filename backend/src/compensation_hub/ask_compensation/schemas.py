from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from compensation_hub.analytics.service import GroupBy
from compensation_hub.ask_compensation.plan import CurrencyCode, Sql
from compensation_hub.ask_compensation.sql_validation import InvalidSqlError, validate_sql

# Follow-ups carry the latest few questions with the SQL they ran, never their results; older
# turns are dropped by the client and rejected here so the planner input stays bounded.
MAX_HISTORY_TURNS = 4

Question = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]


class AskTurn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: Question
    sql: Sql
    currency: CurrencyCode = "USD"

    @field_validator("sql")
    @classmethod
    def sql_is_valid(cls, value: str) -> str:
        # History is context for the planner and is never executed, but it passes the same
        # validation so it cannot carry anything a planned query could not.
        try:
            validate_sql(value)
        except InvalidSqlError as error:
            raise ValueError(error.message) from error
        return value


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: Question
    history: Annotated[list[AskTurn], Field(max_length=MAX_HISTORY_TURNS)] = []


class ResultColumnRead(BaseModel):
    key: str
    label: str
    type: Literal["text", "count", "money", "percent", "number"]
    currency: str | None = None
    # Set on per-employee local salaries: the key of the column holding each row's currency.
    currency_key: str | None = None


class ResultRowRead(BaseModel):
    values: list[str | int | Decimal | None]
    employee_id: int | None = None


class AskResultRead(BaseModel):
    kind: Literal["scalar", "table"]
    columns: list[ResultColumnRead]
    rows: list[ResultRowRead]
    # The column that carries the headline figure, or null when there is none.
    primary: str | None
    total_rows: int


class AnalyticsViewRead(BaseModel):
    """The Analytics workspace view that shows the same figures, when one exists."""

    group_by: GroupBy | None
    metric: Literal["headcount", "payroll", "average"]
    country: str | None = None
    department: str | None = None
    job_title: str | None = None


class AskResponse(BaseModel):
    status: Literal["answered", "missing_data", "unsupported"]
    question: str
    answer: str
    # The planner's plain-language reading of the validated query, so it can be checked.
    interpretation: str | None = None
    missing: list[str] = []
    # The validated SQL and answer currency, which the client sends back with follow-ups.
    sql: str | None = None
    currency: str = "USD"
    result: AskResultRead | None = None
    analytics_view: AnalyticsViewRead | None = None
