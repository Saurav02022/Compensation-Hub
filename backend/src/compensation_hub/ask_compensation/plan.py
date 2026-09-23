"""The read-only query representation the planner produces.

This is the security boundary between language understanding and data access. The model can
only describe a SELECT over the catalog fields: filters, projected fields, grouping, aggregate
measures, arithmetic over those measures, ordering, and a bounded limit. Nothing here can name
a table, express SQL, or describe a write. Structural limits are enforced here; the meaning of a
query (which fields exist, which operations suit them, which values are real) is checked
against the catalog and the data in ``validation``.
"""

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StringConstraints

MAX_FILTERS = 10
MAX_FILTER_VALUES = 50
MAX_FIELDS = 10
MAX_GROUP_BY = 2
MAX_MEASURES = 8
MAX_CALCULATIONS = 8
MAX_HAVING = 5
MAX_ORDER_BY = 3
MAX_LIMIT = 100

# Names the plan uses for its own measures and calculations; referenced by later calculations,
# having conditions, and ordering, but never used as SQL identifiers.
Name = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]{0,39}$")]
# Field names are checked against the catalog during validation, so an unknown field such as
# "gender" becomes an explicit missing-data answer rather than a schema error.
FieldName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


def _upper(value: object) -> object:
    return value.strip().upper() if isinstance(value, str) else value


# Normalized before the pattern check, so "inr" is accepted as INR.
CurrencyCode = Annotated[str, BeforeValidator(_upper), StringConstraints(pattern=r"^[A-Z]{3}$")]
Number = Annotated[Decimal, Field(allow_inf_nan=False, max_digits=24, decimal_places=8)]

FilterOperator = Literal[
    "eq", "ne", "in", "not_in", "contains", "starts_with", "gt", "gte", "lt", "lte"
]
AggregateFunction = Literal["count", "count_distinct", "sum", "avg", "median", "min", "max"]
CalculationOperator = Literal["add", "subtract", "multiply", "divide", "percent"]
ComparisonOperator = Literal["gt", "gte", "lt", "lte", "eq", "ne"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Condition(_Strict):
    field: FieldName
    op: FilterOperator
    value: Text | Number | None = None
    values: Annotated[list[Text], Field(max_length=MAX_FILTER_VALUES)] | None = None
    # Currency of a salary threshold; defaults to the query's answer currency.
    currency: CurrencyCode | None = None


class Measure(_Strict):
    name: Name
    function: AggregateFunction
    field: FieldName | None = None
    # Conditions that apply to this measure only (SQL FILTER), for shares and comparisons.
    filters: Annotated[list[Condition], Field(max_length=MAX_FILTERS)] = []


class Calculation(_Strict):
    name: Name
    op: CalculationOperator
    left: Name | Number
    right: Name | Number


class HavingCondition(_Strict):
    key: Name
    op: ComparisonOperator
    value: Number


class OrderKey(_Strict):
    key: Annotated[str, StringConstraints(min_length=1, max_length=60)]
    direction: Literal["asc", "desc"] = "asc"


class Query(_Strict):
    kind: Literal["rows", "aggregate"]
    filters: Annotated[list[Condition], Field(max_length=MAX_FILTERS)] = []
    fields: Annotated[list[FieldName], Field(max_length=MAX_FIELDS)] = []
    group_by: Annotated[list[FieldName], Field(max_length=MAX_GROUP_BY)] = []
    measures: Annotated[list[Measure], Field(max_length=MAX_MEASURES)] = []
    calculations: Annotated[list[Calculation], Field(max_length=MAX_CALCULATIONS)] = []
    having: Annotated[list[HavingCondition], Field(max_length=MAX_HAVING)] = []
    order_by: Annotated[list[OrderKey], Field(max_length=MAX_ORDER_BY)] = []
    limit: Annotated[int, Field(ge=1, le=MAX_LIMIT)] | None = None
    currency: CurrencyCode = "USD"


Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]


class QueryResponse(_Strict):
    status: Literal["query"]
    query: Query


class MissingDataResponse(_Strict):
    status: Literal["missing_data"]
    missing: Annotated[
        list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]],
        Field(min_length=1, max_length=5),
    ]
    reason: Reason | None = None


class UnsupportedResponse(_Strict):
    status: Literal["unsupported"]
    reason: Reason


PlannerResponse = Annotated[
    QueryResponse | MissingDataResponse | UnsupportedResponse, Field(discriminator="status")
]
