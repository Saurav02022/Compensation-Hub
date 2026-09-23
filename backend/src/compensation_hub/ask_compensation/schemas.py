from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from compensation_hub.analytics.service import GroupBy
from compensation_hub.ask_compensation.plan import Query

# Follow-ups carry the latest few validated queries, never their results; older turns are
# dropped by the client and rejected here so the planner input stays bounded.
MAX_HISTORY_TURNS = 4

Question = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]


class AskTurn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: Question
    query: Query


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
    # The column that carries the headline figure, or null for plain employee lists.
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
    # A plain-language reading of the validated query, so the interpretation can be checked.
    interpretation: str | None = None
    missing: list[str] = []
    query: Query | None = None
    result: AskResultRead | None = None
    analytics_view: AnalyticsViewRead | None = None
