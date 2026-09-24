"""The structured response the planner must return.

A query response carries candidate SQL, which is only ever run after ``sql_validation`` has
parsed and checked it, plus presentation metadata: the answer currency, a plain-language reading
of the query, and which result columns are percentages. Missing-data and unsupported responses
carry no SQL at all.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StringConstraints

from compensation_hub.ask_compensation.sql_validation import MAX_SQL_LENGTH


def _upper(value: object) -> object:
    return value.strip().upper() if isinstance(value, str) else value


# Normalized before the pattern check, so "inr" is accepted as INR.
CurrencyCode = Annotated[str, BeforeValidator(_upper), StringConstraints(pattern=r"^[A-Z]{3}$")]
Sql = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_SQL_LENGTH)
]
ColumnName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=63)]
Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class QueryResponse(_Strict):
    status: Literal["query"]
    sql: Sql
    currency: CurrencyCode = "USD"
    interpretation: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=240)
    ]
    percent_columns: Annotated[list[ColumnName], Field(max_length=20)] = []
    primary: ColumnName | None = None


class _NoQuery(BaseModel):
    # These responses carry no SQL and nothing in them is executed. Schema-guided output fills
    # every declared property (currency, interpretation), so other keys are ignored rather than
    # rejected.
    model_config = ConfigDict(extra="ignore")


class MissingDataResponse(_NoQuery):
    status: Literal["missing_data"]
    missing: Annotated[
        list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]],
        Field(min_length=1, max_length=5),
    ]
    reason: Reason | None = None


class UnsupportedResponse(_NoQuery):
    status: Literal["unsupported"]
    reason: Reason


PlannerResponse = Annotated[
    QueryResponse | MissingDataResponse | UnsupportedResponse, Field(discriminator="status")
]
