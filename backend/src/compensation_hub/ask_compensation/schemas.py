from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

DataField = Literal[
    "employee_code",
    "full_name",
    "country",
    "department",
    "job_title",
    "annual_salary",
    "currency_code",
    "salary_usd",
    "rate_to_usd",
    "has_compensation",
]
FilterOperator = Literal[
    "eq",
    "neq",
    "in",
    "not_in",
    "contains",
    "starts_with",
    "ends_with",
    "gt",
    "gte",
    "lt",
    "lte",
    "is_null",
    "not_null",
]
AggregateFunction = Literal[
    "count",
    "count_distinct",
    "sum",
    "avg",
    "min",
    "max",
    "median",
    "stddev",
    "variance",
    "percentile",
]
SortDirection = Literal["asc", "desc"]
CalculationOperator = Literal[
    "add",
    "subtract",
    "multiply",
    "divide",
    "percentage",
    "percent_difference",
    "ratio",
]
ResultFormat = Literal["text", "number", "count", "currency", "percent"]

Identifier = Annotated[
    str,
    StringConstraints(strip_whitespace=True, pattern=r"^[A-Za-z][A-Za-z0-9_]{0,49}$"),
]
QuestionText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]
CurrencyCode = Annotated[
    str, StringConstraints(strip_whitespace=True, to_upper=True, pattern=r"^[A-Z]{3}$")
]


class FilterClause(BaseModel):
    """One validated predicate over the read-only employee-compensation dataset."""

    model_config = ConfigDict(extra="forbid")

    field: DataField
    op: FilterOperator
    values: Annotated[list[str], Field(max_length=20)] = Field(default_factory=list)

    @model_validator(mode="after")
    def value_shape_matches_operator(self) -> "FilterClause":
        if self.op in ("is_null", "not_null"):
            if self.values:
                raise ValueError(f"{self.op} does not accept values")
            return self
        if not self.values:
            raise ValueError(f"{self.op} requires at least one value")
        if self.op not in ("in", "not_in") and len(self.values) != 1:
            raise ValueError(f"{self.op} accepts exactly one value")
        return self


class Projection(BaseModel):
    """A field or aggregate returned by one query."""

    model_config = ConfigDict(extra="forbid")

    alias: Identifier
    field: DataField | None = None
    aggregate: AggregateFunction | None = None
    percentile: Decimal | None = Field(default=None, gt=0, lt=1)

    @model_validator(mode="after")
    def projection_is_well_formed(self) -> "Projection":
        if self.aggregate is None:
            if self.field is None:
                raise ValueError("a non-aggregate projection requires field")
            if self.percentile is not None:
                raise ValueError("percentile is only valid with percentile aggregation")
            return self

        if self.aggregate == "count":
            if self.percentile is not None:
                raise ValueError("count does not accept percentile")
            return self

        if self.field is None:
            raise ValueError(f"{self.aggregate} requires field")

        if self.aggregate == "percentile":
            if self.percentile is None:
                raise ValueError("percentile aggregation requires percentile")
        elif self.percentile is not None:
            raise ValueError("percentile parameter is only valid for percentile aggregation")
        return self


class OrderClause(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: Identifier
    direction: SortDirection = "asc"


class DataQuery(BaseModel):
    """One bounded SELECT-like operation expressed without SQL."""

    model_config = ConfigDict(extra="forbid")

    name: Identifier
    select: Annotated[list[Projection], Field(min_length=1, max_length=10)]
    filters: Annotated[list[FilterClause], Field(max_length=20)] = Field(default_factory=list)
    group_by: Annotated[list[DataField], Field(max_length=4)] = Field(default_factory=list)
    order_by: Annotated[list[OrderClause], Field(max_length=4)] = Field(default_factory=list)
    distinct: bool = False
    limit: Annotated[int, Field(ge=1, le=100)] | None = None
    target_currency: CurrencyCode | None = None

    @model_validator(mode="after")
    def query_shape_is_consistent(self) -> "DataQuery":
        aliases = [projection.alias for projection in self.select]
        if len(aliases) != len(set(aliases)):
            raise ValueError("projection aliases must be unique")
        if len(self.group_by) != len(set(self.group_by)):
            raise ValueError("group_by fields must be unique")
        if self.distinct and any(projection.aggregate is not None for projection in self.select):
            raise ValueError("distinct cannot be combined with aggregate projections")
        return self


class ResultRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: Identifier
    column: Identifier


class Calculation(BaseModel):
    """Optional deterministic arithmetic over scalar query results."""

    model_config = ConfigDict(extra="forbid")

    op: CalculationOperator
    left: ResultRef
    right: ResultRef
    label: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
    format: ResultFormat = "number"


class QueryProgram(BaseModel):
    """A small read-only program that can derive an answer from available product data."""

    model_config = ConfigDict(extra="forbid")

    queries: Annotated[list[DataQuery], Field(min_length=1, max_length=4)]
    calculation: Calculation | None = None

    @model_validator(mode="after")
    def program_references_existing_queries(self) -> "QueryProgram":
        names = [query.name for query in self.queries]
        if len(names) != len(set(names)):
            raise ValueError("query names must be unique")

        if self.calculation is not None:
            known = set(names)
            for ref in (self.calculation.left, self.calculation.right):
                if ref.query not in known:
                    raise ValueError(f"calculation references unknown query {ref.query}")
        return self


class PlannedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["plan"]
    plan: QueryProgram


class UnsupportedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["unsupported"]
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


PlannerResponse = Annotated[PlannedResponse | UnsupportedResponse, Field(discriminator="status")]


class AskHistoryItem(BaseModel):
    """Prior validated intent; query results and salary values are not sent back to the model."""

    model_config = ConfigDict(extra="forbid")

    question: QuestionText
    plan: QueryProgram


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: QuestionText
    history: Annotated[list[AskHistoryItem], Field(max_length=6)] = Field(default_factory=list)


class AskResultColumn(BaseModel):
    key: str
    label: str
    format: ResultFormat = "text"


class AskResult(BaseModel):
    kind: Literal["scalar", "table"]
    currency: CurrencyCode | None = None
    columns: list[AskResultColumn]
    rows: list[dict[str, str | int | None]]


class AskResponse(BaseModel):
    status: Literal["answered", "unsupported"]
    question: str
    answer: str
    interpretation: str | None = None
    plan: QueryProgram | None = None
    result: AskResult | None = None
    analytics_path: str | None = None
