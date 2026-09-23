from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

PlanKind = Literal["aggregate", "employees", "values", "share", "compare"]
Metric = Literal[
    "employee_count",
    "average_salary",
    "total_payroll",
    "minimum_salary",
    "maximum_salary",
    "median_salary",
]
Dimension = Literal["country", "department", "job_title", "currency_code"]
SortDirection = Literal["asc", "desc"]
EmployeeSort = Literal["full_name", "employee_code", "salary_usd", "annual_salary"]
ComparisonOperation = Literal["difference", "percent_difference", "ratio"]

FilterValue = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
CurrencyCode = Annotated[
    str, StringConstraints(strip_whitespace=True, to_upper=True, pattern=r"^[A-Z]{3}$")
]


class QueryFilters(BaseModel):
    """Read-only predicates that can be translated into SQLAlchemy expressions."""

    model_config = ConfigDict(extra="forbid")

    countries: list[FilterValue] = Field(default_factory=list, max_length=20)
    departments: list[FilterValue] = Field(default_factory=list, max_length=20)
    job_titles: list[FilterValue] = Field(default_factory=list, max_length=20)
    currency_codes: list[CurrencyCode] = Field(default_factory=list, max_length=20)
    employee_code: FilterValue | None = None
    name_contains: FilterValue | None = None
    salary_usd_min: Decimal | None = Field(default=None, ge=0)
    salary_usd_max: Decimal | None = Field(default=None, ge=0)
    has_compensation: bool | None = None

    @model_validator(mode="after")
    def salary_range_is_ordered(self) -> "QueryFilters":
        if (
            self.salary_usd_min is not None
            and self.salary_usd_max is not None
            and self.salary_usd_min > self.salary_usd_max
        ):
            raise ValueError("salary_usd_min cannot exceed salary_usd_max")
        return self


class QueryPlan(BaseModel):
    """A constrained, read-only request over data Compensation Hub actually stores."""

    model_config = ConfigDict(extra="forbid")

    kind: PlanKind
    metric: Metric | None = None
    filters: QueryFilters = Field(default_factory=QueryFilters)
    denominator_filters: QueryFilters | None = None
    compare_filters: QueryFilters | None = None
    group_by: Dimension | None = None
    field: Dimension | None = None
    sort: SortDirection | None = None
    sort_by: EmployeeSort | None = None
    limit: Annotated[int, Field(ge=1, le=100)] | None = None
    target_currency: CurrencyCode | None = None
    comparison: ComparisonOperation | None = None

    @model_validator(mode="after")
    def shape_matches_kind(self) -> "QueryPlan":
        if self.kind == "aggregate":
            if self.metric is None:
                raise ValueError("aggregate plans require metric")
            if any(
                value is not None
                for value in (
                    self.denominator_filters,
                    self.compare_filters,
                    self.field,
                    self.sort_by,
                    self.comparison,
                )
            ):
                raise ValueError("aggregate plan contains fields for another plan kind")
            if self.group_by is None and (self.sort is not None or self.limit is not None):
                raise ValueError("aggregate sort and limit require group_by")
            if self.metric == "employee_count" and self.target_currency is not None:
                raise ValueError("employee_count cannot have a target currency")
            return self

        if self.kind == "employees":
            if any(
                value is not None
                for value in (
                    self.metric,
                    self.denominator_filters,
                    self.compare_filters,
                    self.group_by,
                    self.field,
                    self.comparison,
                )
            ):
                raise ValueError("employees plan contains fields for another plan kind")
            return self

        if self.kind == "values":
            if self.field is None:
                raise ValueError("values plans require field")
            if any(
                value is not None
                for value in (
                    self.metric,
                    self.denominator_filters,
                    self.compare_filters,
                    self.group_by,
                    self.sort_by,
                    self.target_currency,
                    self.comparison,
                )
            ):
                raise ValueError("values plan contains fields for another plan kind")
            return self

        if self.kind == "share":
            if self.metric not in ("employee_count", "total_payroll"):
                raise ValueError("share plans support employee_count or total_payroll")
            if self.denominator_filters is None:
                raise ValueError("share plans require denominator_filters")
            if any(
                value is not None
                for value in (
                    self.compare_filters,
                    self.group_by,
                    self.field,
                    self.sort,
                    self.sort_by,
                    self.limit,
                    self.target_currency,
                    self.comparison,
                )
            ):
                raise ValueError("share plan contains fields for another plan kind")
            return self

        if self.kind == "compare":
            if self.metric is None:
                raise ValueError("compare plans require metric")
            if self.compare_filters is None:
                raise ValueError("compare plans require compare_filters")
            if self.comparison is None:
                raise ValueError("compare plans require comparison")
            if any(
                value is not None
                for value in (
                    self.denominator_filters,
                    self.group_by,
                    self.field,
                    self.sort,
                    self.sort_by,
                    self.limit,
                )
            ):
                raise ValueError("compare plan contains fields for another plan kind")
            if self.metric == "employee_count" and self.target_currency is not None:
                raise ValueError("employee_count cannot have a target currency")
            return self

        raise ValueError("unknown plan kind")


class PlannedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["plan"]
    plan: QueryPlan


class UnsupportedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["unsupported"]
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


PlannerResponse = Annotated[PlannedResponse | UnsupportedResponse, Field(discriminator="status")]


class AskHistoryItem(BaseModel):
    """Prior intent only; result rows and salary values are never sent back to the planner."""

    model_config = ConfigDict(extra="forbid")

    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]
    plan: QueryPlan


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]
    history: Annotated[list[AskHistoryItem], Field(max_length=6)] = Field(default_factory=list)


ResultFormat = Literal["text", "count", "currency", "percent"]


class AskResultColumn(BaseModel):
    key: str
    label: str
    format: ResultFormat = "text"


class AskResult(BaseModel):
    kind: Literal["scalar", "table", "employees"]
    currency: CurrencyCode | None = None
    columns: list[AskResultColumn]
    rows: list[dict[str, str | int | None]]


class AskResponse(BaseModel):
    status: Literal["answered", "unsupported"]
    question: str
    answer: str
    interpretation: str | None = None
    plan: QueryPlan | None = None
    result: AskResult | None = None
    analytics_path: str | None = None
