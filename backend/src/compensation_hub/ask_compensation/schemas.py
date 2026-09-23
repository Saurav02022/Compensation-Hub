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
]
NumericField = Literal["annual_salary", "salary_usd", "rate_to_usd"]
AggregateFunction = Literal["count", "sum", "average", "minimum", "maximum", "median"]
BinaryOperator = Literal["add", "subtract", "multiply", "divide"]
PredicateOperator = Literal[
    "equals",
    "not_equals",
    "in",
    "contains",
    "greater_than",
    "greater_than_or_equal",
    "less_than",
    "less_than_or_equal",
    "is_null",
    "is_not_null",
]
SortDirection = Literal["asc", "desc"]
ResultFormat = Literal["text", "number", "count", "currency", "percent"]

Alias = Annotated[
    str,
    StringConstraints(strip_whitespace=True, pattern=r"^[a-z][a-z0-9_]{0,39}$"),
]
DisplayLabel = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
CurrencyCode = Annotated[
    str,
    StringConstraints(strip_whitespace=True, to_upper=True, pattern=r"^[A-Z]{3}$"),
]
TextValue = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
PredicateValue = str | Decimal | bool


class Predicate(BaseModel):
    """One validated predicate over the read-only Compensation Hub data surface."""

    model_config = ConfigDict(extra="forbid")

    field: DataField
    operator: PredicateOperator
    value: PredicateValue | None = None
    values: Annotated[list[PredicateValue], Field(max_length=30)] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_shape(self) -> "Predicate":
        if self.operator in ("is_null", "is_not_null"):
            if self.value is not None or self.values:
                raise ValueError("null predicates cannot contain values")
            return self
        if self.operator == "in":
            if not self.values or self.value is not None:
                raise ValueError("in predicates require values and no value")
            return self
        if self.value is None or self.values:
            raise ValueError("this predicate requires exactly one value")
        return self


class FieldExpression(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["field"]
    field: DataField


class AggregateExpression(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["aggregate"]
    function: AggregateFunction
    field: DataField | None = None
    distinct: bool = False
    where: Annotated[list[Predicate], Field(max_length=12)] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_aggregate(self) -> "AggregateExpression":
        if self.function == "count":
            if self.distinct and self.field is None:
                raise ValueError("distinct count requires a field")
            return self
        if self.field not in ("salary_usd", "rate_to_usd"):
            raise ValueError(
                f"{self.function} requires salary_usd or rate_to_usd; "
                "annual_salary cannot be aggregated safely across currencies"
            )
        if self.distinct:
            raise ValueError("distinct is supported only for count")
        return self


class LiteralExpression(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["literal"]
    value: Decimal


class BinaryExpression(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["binary"]
    operator: BinaryOperator
    left: "Expression"
    right: "Expression"


class CurrencyExpression(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["currency"]
    currency_code: CurrencyCode
    expression: "Expression"


Expression = Annotated[
    FieldExpression
    | AggregateExpression
    | LiteralExpression
    | BinaryExpression
    | CurrencyExpression,
    Field(discriminator="kind"),
]


class SelectItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alias: Alias
    label: DisplayLabel
    expression: Expression
    format: ResultFormat = "text"


class OrderBy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: Alias
    direction: SortDirection = "asc"


class QueryPlan(BaseModel):
    """A generic, bounded, read-only query over the Compensation Hub data surface."""

    model_config = ConfigDict(extra="forbid")

    select: Annotated[list[SelectItem], Field(min_length=1, max_length=12)]
    where: Annotated[list[Predicate], Field(max_length=16)] = Field(default_factory=list)
    group_by: Annotated[list[DataField], Field(max_length=4)] = Field(default_factory=list)
    distinct: bool = False
    order_by: Annotated[list[OrderBy], Field(max_length=4)] = Field(default_factory=list)
    limit: Annotated[int, Field(ge=1, le=100)] = 50

    @model_validator(mode="after")
    def validate_aliases(self) -> "QueryPlan":
        aliases = [item.alias for item in self.select]
        if len(aliases) != len(set(aliases)):
            raise ValueError("select aliases must be unique")
        alias_set = set(aliases)
        for ordering in self.order_by:
            if ordering.key not in alias_set:
                raise ValueError(f"order key {ordering.key} is not a select alias")
        if len(self.group_by) != len(set(self.group_by)):
            raise ValueError("group_by fields must be unique")
        return self


class PlannedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["plan"]
    plan: QueryPlan


class UnsupportedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["unsupported"]
    missing: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


PlannerResponse = Annotated[PlannedResponse | UnsupportedResponse, Field(discriminator="status")]


class AskHistoryItem(BaseModel):
    """Prior validated intent; result values are deliberately not sent back to the planner."""

    model_config = ConfigDict(extra="forbid")

    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]
    plan: QueryPlan


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]
    history: Annotated[list[AskHistoryItem], Field(max_length=6)] = Field(default_factory=list)


class AskResultColumn(BaseModel):
    key: str
    label: str
    format: ResultFormat = "text"


class AskResult(BaseModel):
    kind: Literal["scalar", "table"]
    currency_by_column: dict[str, CurrencyCode] = Field(default_factory=dict)
    columns: list[AskResultColumn]
    rows: list[dict[str, str | int | None]]


class AskResponse(BaseModel):
    status: Literal["answered", "unsupported"]
    question: str
    answer: str
    interpretation: str | None = None
    plan: QueryPlan | None = None
    result: AskResult | None = None


BinaryExpression.model_rebuild()
CurrencyExpression.model_rebuild()
