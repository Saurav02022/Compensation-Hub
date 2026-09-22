from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from compensation_hub.analytics.service import MAX_BREAKDOWN_LIMIT, GroupBy

Metric = Literal["employee_count", "average_salary", "total_payroll"]
SortDirection = Literal["asc", "desc"]

FilterValue = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class QueryFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    country: FilterValue | None = None
    department: FilterValue | None = None
    job_title: FilterValue | None = None


class QueryPlan(BaseModel):
    """The only analytics request shape the model may produce.

    Every field maps onto the deterministic analytics service; nothing here can express a
    write, a free-form expression, or a query outside the supported metrics and dimensions.
    """

    model_config = ConfigDict(extra="forbid")

    metric: Metric
    filters: QueryFilters = Field(default_factory=QueryFilters)
    group_by: GroupBy | None = None
    sort: SortDirection | None = None
    limit: Annotated[int, Field(ge=1, le=MAX_BREAKDOWN_LIMIT)] | None = None


class PlannedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["plan"]
    plan: QueryPlan


class UnsupportedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["unsupported"]
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


PlannerResponse = Annotated[PlannedResponse | UnsupportedResponse, Field(discriminator="status")]


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]


class AskResultRow(BaseModel):
    key: str | None
    employee_count: int
    total_payroll_usd: Decimal
    average_salary_usd: Decimal | None


class AskResult(BaseModel):
    currency: Literal["USD"] = "USD"
    rows: list[AskResultRow]


class AskResponse(BaseModel):
    status: Literal["answered", "unsupported"]
    question: str
    answer: str
    plan: QueryPlan | None = None
    result: AskResult | None = None
