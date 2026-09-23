"""Validation of planned queries against the catalog and the data vocabulary."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from compensation_hub.ask_compensation.plan import MAX_LIMIT, Query
from compensation_hub.ask_compensation.validation import (
    DataContext,
    InvalidQueryError,
    MissingDataError,
    ValidatedQuery,
    validate_query,
)

CONTEXT = DataContext(
    vocabulary={
        "country": ("Germany", "India", "United Kingdom"),
        "department": ("Engineering", "Sales"),
        "job_title": ("Account Executive", "Software Engineer"),
        "currency": ("EUR", "GBP", "INR"),
    },
    fx_rates={
        "USD": Decimal("1"),
        "EUR": Decimal("1.08"),
        "GBP": Decimal("1.27"),
        "INR": Decimal("0.012"),
    },
)
COUNT = {"name": "n", "function": "count"}


def validate(plan: dict[str, object]) -> ValidatedQuery:
    return validate_query(Query.model_validate(plan), CONTEXT)


def aggregate(**parts: object) -> dict[str, object]:
    return {"kind": "aggregate", "measures": [COUNT], **parts}


def test_unknown_field_is_reported_as_missing_data() -> None:
    with pytest.raises(MissingDataError) as raised:
        validate(aggregate(filters=[{"field": "gender", "op": "eq", "value": "male"}]))

    assert raised.value.missing == ("gender",)
    assert "does not store 'gender'" in raised.value.message
    assert "country" in raised.value.message


def test_a_newly_catalogued_field_would_not_need_a_new_handler() -> None:
    # Answerability comes from the catalog alone: the same plan shape works for any category.
    for field, value in (("country", "India"), ("department", "Sales"), ("currency", "EUR")):
        validated = validate(aggregate(filters=[{"field": field, "op": "eq", "value": value}]))
        assert validated.conditions[0].values == (value,)


def test_unknown_category_value_lists_the_real_values() -> None:
    with pytest.raises(MissingDataError) as raised:
        validate(aggregate(filters=[{"field": "country", "op": "eq", "value": "Atlantis"}]))

    assert "no country 'Atlantis'" in raised.value.message
    assert "Germany, India, United Kingdom" in raised.value.message


def test_category_values_are_matched_without_regard_to_case() -> None:
    validated = validate(
        aggregate(filters=[{"field": "country", "op": "in", "values": ["india", "GERMANY"]}])
    )

    assert validated.conditions[0].values == ("India", "Germany")


def test_unconfigured_currency_is_missing_data() -> None:
    with pytest.raises(MissingDataError, match="no exchange rate for CHF"):
        validate(aggregate(currency="CHF"))
    with pytest.raises(MissingDataError, match="no exchange rate for JPY"):
        validate(
            aggregate(filters=[{"field": "salary", "op": "gt", "value": 1, "currency": "jpy"}])
        )


def test_salary_threshold_is_converted_to_usd() -> None:
    validated = validate(
        aggregate(
            filters=[{"field": "salary", "op": "gt", "value": "1,000,000", "currency": "INR"}]
        )
    )

    assert validated.conditions[0].threshold_usd == Decimal("12000.000")


@pytest.mark.parametrize(
    ("condition", "message"),
    [
        ({"field": "salary", "op": "contains", "value": "1"}, "cannot be filtered"),
        ({"field": "country", "op": "gt", "value": "A"}, "cannot be filtered"),
        ({"field": "local_salary", "op": "gt", "value": 1}, "cannot be filtered"),
        ({"field": "country", "op": "in"}, "needs values"),
        ({"field": "country", "op": "eq"}, "needs a value"),
        ({"field": "country", "op": "eq", "value": "India", "currency": "USD"}, "only to salary"),
        ({"field": "salary", "op": "gt", "value": "lots"}, "needs a number"),
        ({"field": "salary", "op": "gt", "value": "1e20"}, "outside the supported range"),
    ],
)
def test_conditions_must_suit_their_field(condition: dict[str, object], message: str) -> None:
    with pytest.raises(InvalidQueryError, match=message):
        validate(aggregate(filters=[condition]))


@pytest.mark.parametrize(
    ("measure", "message"),
    [
        ({"name": "m", "function": "sum", "field": "country"}, "cannot be aggregated"),
        ({"name": "m", "function": "avg", "field": "local_salary"}, "cannot be aggregated"),
        ({"name": "m", "function": "median"}, "needs a field"),
    ],
)
def test_aggregates_must_suit_their_field(measure: dict[str, object], message: str) -> None:
    with pytest.raises(InvalidQueryError, match=message):
        validate({"kind": "aggregate", "measures": [measure]})


@pytest.mark.parametrize("field", ["salary", "full_name", "local_salary"])
def test_grouping_is_limited_to_categories(field: str) -> None:
    with pytest.raises(InvalidQueryError, match="cannot be grouped"):
        validate(aggregate(group_by=[field]))


def test_order_keys_must_be_known() -> None:
    with pytest.raises(InvalidQueryError, match="cannot be ordered"):
        validate(aggregate(group_by=["country"], order_by=[{"key": "salary"}]))
    with pytest.raises(InvalidQueryError, match="cannot be ordered"):
        validate({"kind": "rows", "fields": ["full_name"], "order_by": [{"key": "local_salary"}]})
    with pytest.raises(MissingDataError):
        validate({"kind": "rows", "fields": ["full_name"], "order_by": [{"key": "tenure"}]})


def test_row_and_aggregate_shapes_do_not_mix() -> None:
    with pytest.raises(InvalidQueryError, match="cannot also group"):
        validate({"kind": "rows", "fields": ["full_name"], "measures": [COUNT]})
    with pytest.raises(InvalidQueryError, match="needs at least one field"):
        validate({"kind": "rows"})
    with pytest.raises(InvalidQueryError, match="row query instead"):
        validate(aggregate(fields=["full_name"]))
    with pytest.raises(InvalidQueryError, match="needs at least one measure"):
        validate({"kind": "aggregate"})


def calculation(op: str, left: object, right: object, name: str = "c") -> dict[str, object]:
    return {"name": name, "op": op, "left": left, "right": right}


MONEY = {"name": "pay", "function": "sum", "field": "salary"}


@pytest.mark.parametrize(
    ("calculations", "message"),
    [
        ([calculation("add", "n", "later")], "not an earlier measure"),
        ([calculation("multiply", "pay", "pay")], "cannot multiply money and money"),
        ([calculation("add", "pay", "n")], "cannot add money and count"),
        ([calculation("divide", "n", "pay")], "cannot divide count and money"),
        ([calculation("divide", "pay", 0)], "divides by zero"),
        ([calculation("percent", "n", "0")], "divides by zero"),
        ([calculation("add", 1, 2)], "uses no measure"),
        ([calculation("divide", 100, "n")], "cannot divide"),
    ],
)
def test_calculations_respect_units_and_references(
    calculations: list[dict[str, object]], message: str
) -> None:
    with pytest.raises(InvalidQueryError, match=message):
        validate({"kind": "aggregate", "measures": [COUNT, MONEY], "calculations": calculations})


def test_calculation_units_follow_the_operands() -> None:
    validated = validate(
        {
            "kind": "aggregate",
            "measures": [COUNT, MONEY],
            "calculations": [
                calculation("divide", "pay", "n", "per_head"),
                calculation("percent", "n", "n", "share"),
                calculation("divide", "pay", "pay", "ratio"),
                calculation("multiply", "pay", Decimal("1.1"), "raised"),
                calculation("multiply", "n", Decimal("0.5"), "half"),
            ],
        }
    )

    assert [c.unit for c in validated.calculations] == [
        "money",
        "percent",
        "number",
        "money",
        "number",
    ]


def test_expression_depth_is_bounded() -> None:
    chain = [calculation("add", "n", "n", "c1")]
    chain += [calculation("add", f"c{i}", "n", f"c{i + 1}") for i in range(1, 4)]

    with pytest.raises(InvalidQueryError, match="more than 3 levels"):
        validate({"kind": "aggregate", "measures": [COUNT], "calculations": chain})


def test_names_must_be_unique() -> None:
    with pytest.raises(InvalidQueryError, match="used more than once"):
        validate({"kind": "aggregate", "measures": [COUNT, COUNT]})
    with pytest.raises(InvalidQueryError, match="used more than once"):
        validate(
            {
                "kind": "aggregate",
                "group_by": ["country"],
                "measures": [{"name": "country", "function": "count"}],
            }
        )


def test_row_defaults_are_bounded_and_ordering_fields_are_shown() -> None:
    validated = validate(
        {
            "kind": "rows",
            "fields": ["full_name"],
            "order_by": [{"key": "salary", "direction": "desc"}],
        }
    )

    assert validated.limit == 25
    assert [spec.name for spec in validated.fields] == ["full_name", "salary"]


@pytest.mark.parametrize(
    "plan",
    [
        {"kind": "rows", "fields": ["full_name"], "limit": MAX_LIMIT + 1},
        {"kind": "rows", "fields": ["full_name"], "limit": 0},
        {"kind": "aggregate", "measures": [COUNT], "sql": "SELECT 1"},
        {"kind": "delete", "measures": [COUNT]},
        {"kind": "aggregate", "measures": [COUNT], "update": {"annual_salary": 1}},
        {
            "kind": "aggregate",
            "measures": [{"name": "n; DROP TABLE employees", "function": "count"}],
        },
        {"kind": "aggregate", "measures": [{"name": "n", "function": "delete"}]},
        {"kind": "aggregate", "measures": [COUNT] * 9},
        {
            "kind": "aggregate",
            "measures": [COUNT],
            "group_by": ["country", "department", "job_title"],
        },
        {
            "kind": "aggregate",
            "measures": [COUNT],
            "filters": [{"field": "country", "op": "eq", "value": "India"}] * 11,
        },
        {
            "kind": "aggregate",
            "measures": [COUNT],
            "filters": [{"field": "country", "op": "in", "values": ["India"] * 51}],
        },
        {
            "kind": "aggregate",
            "measures": [COUNT],
            "filters": [{"field": "country", "op": "eq", "value": "x" * 101}],
        },
        {"kind": "aggregate", "measures": [COUNT], "currency": "US Dollars"},
        {
            "kind": "aggregate",
            "measures": [COUNT],
            "calculations": [calculation("add", "n", "NaN")],
        },
    ],
)
def test_structural_limits_and_unknown_keys_are_rejected(plan: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        Query.model_validate(plan)
