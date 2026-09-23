"""The generic Ask Compensation query engine, exercised with structured queries directly.

Expected values are computed independently from the seed dataset in Decimal arithmetic, so these
tests prove the engine answers any query the representation can express, not a list of questions.
"""

from collections import defaultdict
from collections.abc import Callable
from decimal import ROUND_HALF_UP, Decimal

import pytest
from sqlalchemy import insert, update
from sqlalchemy.exc import InternalError
from sqlalchemy.orm import Session

from compensation_hub.analytics.service import AnalyticsFilters, get_breakdown
from compensation_hub.ask_compensation.execution import (
    QueryResult,
    begin_read_only,
    execute_query,
)
from compensation_hub.ask_compensation.plan import Query
from compensation_hub.ask_compensation.service import load_data_context
from compensation_hub.ask_compensation.validation import validate_query
from compensation_hub.db.models import Compensation, Employee
from compensation_hub.seed.dataset import SeedEmployee, build_seed_dataset
from compensation_hub.seed.service import seed_database

DATASET = build_seed_dataset(employee_count=60)
EMPLOYEES = list(DATASET.employees)
RATES = {rate.currency_code: rate.rate_to_usd for rate in DATASET.fx_rates}
CENTS = Decimal("0.01")
SAMPLE = EMPLOYEES[0]


def usd(employee: SeedEmployee) -> Decimal:
    return employee.annual_salary * RATES[employee.currency_code]


def cents(value: Decimal) -> Decimal:
    return value.quantize(CENTS, rounding=ROUND_HALF_UP)


def median(values: list[Decimal]) -> Decimal:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def where(predicate: Callable[[SeedEmployee], bool]) -> list[SeedEmployee]:
    return [employee for employee in EMPLOYEES if predicate(employee)]


@pytest.fixture
def session(db_session: Session) -> Session:
    seed_database(db_session, DATASET)
    db_session.commit()
    return db_session


def run(session: Session, plan: dict[str, object]) -> QueryResult:
    validated = validate_query(Query.model_validate(plan), load_data_context(session))
    return execute_query(session, validated)


def scalar(result: QueryResult, key: str) -> object:
    index = [column.key for column in result.columns].index(key)
    assert len(result.rows) == 1
    return result.rows[0].values[index]


def column(result: QueryResult, key: str) -> list[object]:
    index = [column.key for column in result.columns].index(key)
    return [row.values[index] for row in result.rows]


def test_counts_all_employees(session: Session) -> None:
    result = run(session, {"kind": "aggregate", "measures": [{"name": "n", "function": "count"}]})

    assert scalar(result, "n") == len(EMPLOYEES)
    assert result.columns[0].type == "count"


def test_counts_with_category_filters(session: Session) -> None:
    result = run(
        session,
        {
            "kind": "aggregate",
            "filters": [
                {"field": "department", "op": "eq", "value": SAMPLE.department},
                {"field": "country", "op": "ne", "value": SAMPLE.country},
            ],
            "measures": [{"name": "n", "function": "count"}],
        },
    )

    expected = where(lambda e: e.department == SAMPLE.department and e.country != SAMPLE.country)
    assert scalar(result, "n") == len(expected)


def test_counts_distinct_values(session: Session) -> None:
    result = run(
        session,
        {
            "kind": "aggregate",
            "measures": [
                {"name": "countries", "function": "count_distinct", "field": "country"},
                {"name": "currencies", "function": "count_distinct", "field": "currency"},
            ],
        },
    )

    assert scalar(result, "countries") == len({e.country for e in EMPLOYEES})
    assert scalar(result, "currencies") == len({e.currency_code for e in EMPLOYEES})


def test_lists_distinct_values_by_grouping(session: Session) -> None:
    result = run(
        session,
        {
            "kind": "aggregate",
            "group_by": ["currency"],
            "measures": [{"name": "employees", "function": "count"}],
        },
    )

    counts: dict[str, int] = defaultdict(int)
    for employee in EMPLOYEES:
        counts[employee.currency_code] += 1
    assert [row.values for row in result.rows] == [(code, counts[code]) for code in sorted(counts)]


def test_row_projection_with_case_insensitive_name_match(session: Session) -> None:
    fragment = SAMPLE.full_name.split()[-1].lower()
    result = run(
        session,
        {
            "kind": "rows",
            "filters": [{"field": "full_name", "op": "contains", "value": fragment}],
            "fields": ["full_name", "employee_code", "country"],
        },
    )

    expected = sorted(
        (e for e in EMPLOYEES if fragment in e.full_name.lower()),
        key=lambda e: (e.full_name, e.employee_code),
    )
    assert column(result, "full_name") == [e.full_name for e in expected]
    assert column(result, "employee_code") == [e.employee_code for e in expected]
    assert all(row.employee_id is not None for row in result.rows)
    assert result.total_rows == len(expected)


@pytest.mark.parametrize("fragment", ["%", "_", "\\"])
def test_text_match_treats_wildcards_literally(session: Session, fragment: str) -> None:
    result = run(
        session,
        {
            "kind": "rows",
            "filters": [{"field": "full_name", "op": "contains", "value": fragment}],
            "fields": ["full_name"],
        },
    )

    assert result.rows == ()
    assert result.total_rows == 0


def test_text_equality_and_prefix(session: Session) -> None:
    exact = run(
        session,
        {
            "kind": "rows",
            "filters": [
                {"field": "employee_code", "op": "eq", "value": SAMPLE.employee_code.lower()}
            ],
            "fields": ["employee_code"],
        },
    )
    prefix = run(
        session,
        {
            "kind": "aggregate",
            "filters": [{"field": "full_name", "op": "starts_with", "value": "A"}],
            "measures": [{"name": "n", "function": "count"}],
        },
    )

    assert column(exact, "employee_code") == [SAMPLE.employee_code]
    assert scalar(prefix, "n") == len(where(lambda e: e.full_name.lower().startswith("a")))


def test_highest_paid_rows_are_ranked_by_normalized_salary(session: Session) -> None:
    result = run(
        session,
        {
            "kind": "rows",
            "filters": [{"field": "country", "op": "eq", "value": SAMPLE.country}],
            "fields": ["full_name", "local_salary"],
            "order_by": [{"key": "salary", "direction": "desc"}],
            "limit": 3,
        },
    )

    in_country = sorted(
        where(lambda e: e.country == SAMPLE.country), key=lambda e: (-usd(e), e.full_name)
    )
    top = in_country[:3]
    assert [c.key for c in result.columns] == ["full_name", "local_salary", "currency", "salary"]
    assert column(result, "full_name") == [e.full_name for e in top]
    assert column(result, "local_salary") == [e.annual_salary for e in top]
    assert column(result, "currency") == [e.currency_code for e in top]
    assert column(result, "salary") == [cents(usd(e)) for e in top]
    assert result.columns[1].currency_key == "currency"
    assert result.total_rows == len(in_country)


def test_row_limit_is_bounded_and_reports_the_total(session: Session) -> None:
    result = run(session, {"kind": "rows", "fields": ["employee_code"]})

    assert len(result.rows) == 25
    assert result.total_rows == len(EMPLOYEES)


def test_salary_threshold_in_usd(session: Session) -> None:
    result = run(
        session,
        {
            "kind": "aggregate",
            "filters": [{"field": "salary", "op": "gt", "value": 100000}],
            "measures": [{"name": "n", "function": "count"}],
        },
    )

    assert scalar(result, "n") == len(where(lambda e: usd(e) > 100000))


def test_salary_threshold_in_another_currency_uses_fixed_rates(session: Session) -> None:
    result = run(
        session,
        {
            "kind": "aggregate",
            "filters": [{"field": "salary", "op": "gte", "value": "5000000", "currency": "INR"}],
            "measures": [{"name": "n", "function": "count"}],
        },
    )

    threshold = Decimal(5000000) * RATES["INR"]
    assert scalar(result, "n") == len(where(lambda e: usd(e) >= threshold))


def test_grouped_totals_match_the_analytics_service(session: Session) -> None:
    result = run(
        session,
        {
            "kind": "aggregate",
            "group_by": ["department"],
            "measures": [
                {"name": "employees", "function": "count"},
                {"name": "payroll", "function": "sum", "field": "salary"},
                {"name": "average", "function": "avg", "field": "salary"},
            ],
        },
    )

    breakdown = get_breakdown(session, "department", AnalyticsFilters())
    assert [row.values for row in result.rows] == [
        (row.key, row.employee_count, row.total_payroll_usd, row.average_salary_usd)
        for row in breakdown
    ]


def test_min_max_average_and_exact_median(session: Session) -> None:
    department = SAMPLE.department
    result = run(
        session,
        {
            "kind": "aggregate",
            "filters": [{"field": "department", "op": "eq", "value": department}],
            "measures": [
                {"name": "lowest", "function": "min", "field": "salary"},
                {"name": "highest", "function": "max", "field": "salary"},
                {"name": "average", "function": "avg", "field": "salary"},
                {"name": "middle", "function": "median", "field": "salary"},
            ],
        },
    )

    salaries = [usd(e) for e in where(lambda e: e.department == department)]
    assert scalar(result, "lowest") == cents(min(salaries))
    assert scalar(result, "highest") == cents(max(salaries))
    assert scalar(result, "average") == cents(sum(salaries, Decimal(0)) / len(salaries))
    assert scalar(result, "middle") == cents(median(salaries))


def test_median_of_an_even_count_averages_the_middle_pair(session: Session) -> None:
    result = run(
        session,
        {"kind": "aggregate", "measures": [{"name": "m", "function": "median", "field": "salary"}]},
    )

    assert len(EMPLOYEES) % 2 == 0
    assert scalar(result, "m") == cents(median([usd(e) for e in EMPLOYEES]))


def test_median_of_an_odd_count_is_the_middle_value(session: Session) -> None:
    top = max(usd(e) for e in EMPLOYEES)
    result = run(
        session,
        {
            "kind": "aggregate",
            "filters": [{"field": "salary", "op": "lt", "value": str(top)}],
            "measures": [{"name": "m", "function": "median", "field": "salary"}],
        },
    )

    salaries = [usd(e) for e in EMPLOYEES if usd(e) < top]
    assert len(salaries) % 2 == 1
    assert scalar(result, "m") == cents(median(salaries))


def test_conditional_measures_and_percentage(session: Session) -> None:
    department, country = SAMPLE.department, SAMPLE.country
    result = run(
        session,
        {
            "kind": "aggregate",
            "filters": [{"field": "department", "op": "eq", "value": department}],
            "measures": [
                {
                    "name": "in_country",
                    "function": "count",
                    "filters": [{"field": "country", "op": "eq", "value": country}],
                },
                {"name": "everyone", "function": "count"},
            ],
            "calculations": [
                {"name": "share", "op": "percent", "left": "in_country", "right": "everyone"}
            ],
        },
    )

    members = where(lambda e: e.department == department)
    matching = [e for e in members if e.country == country]
    assert scalar(result, "in_country") == len(matching)
    assert scalar(result, "everyone") == len(members)
    assert scalar(result, "share") == cents(Decimal(len(matching)) * 100 / len(members))
    assert result.columns[2].type == "percent"


def test_difference_and_ratio_between_groups(session: Session) -> None:
    first, second = sorted({e.country for e in EMPLOYEES})[:2]
    result = run(
        session,
        {
            "kind": "aggregate",
            "measures": [
                {
                    "name": "first",
                    "function": "sum",
                    "field": "salary",
                    "filters": [{"field": "country", "op": "eq", "value": first}],
                },
                {
                    "name": "second",
                    "function": "sum",
                    "field": "salary",
                    "filters": [{"field": "country", "op": "eq", "value": second}],
                },
            ],
            "calculations": [
                {"name": "difference", "op": "subtract", "left": "first", "right": "second"},
                {"name": "ratio", "op": "divide", "left": "first", "right": "second"},
            ],
        },
    )

    a = sum((usd(e) for e in where(lambda e: e.country == first)), Decimal(0))
    b = sum((usd(e) for e in where(lambda e: e.country == second)), Decimal(0))
    assert scalar(result, "difference") == cents(a - b)
    assert scalar(result, "ratio") == (a / b).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    assert [c.type for c in result.columns] == ["money", "money", "money", "number"]


def test_having_ordering_and_limit_on_groups(session: Session) -> None:
    result = run(
        session,
        {
            "kind": "aggregate",
            "group_by": ["country"],
            "measures": [{"name": "employees", "function": "count"}],
            "having": [{"key": "employees", "op": "gte", "value": 3}],
            "order_by": [{"key": "employees", "direction": "desc"}],
            "limit": 2,
        },
    )

    counts: dict[str, int] = defaultdict(int)
    for employee in EMPLOYEES:
        counts[employee.country] += 1
    qualifying = sorted(
        ((name, n) for name, n in counts.items() if n >= 3), key=lambda item: (-item[1], item[0])
    )
    assert [row.values for row in result.rows] == qualifying[:2]
    assert result.total_rows == len(qualifying)


def test_two_dimension_grouping(session: Session) -> None:
    result = run(
        session,
        {
            "kind": "aggregate",
            "group_by": ["country", "department"],
            "measures": [{"name": "employees", "function": "count"}],
        },
    )

    counts: dict[tuple[str, str], int] = defaultdict(int)
    for employee in EMPLOYEES:
        counts[(employee.country, employee.department)] += 1
    assert [row.values for row in result.rows] == [(*key, counts[key]) for key in sorted(counts)]


def test_amounts_convert_to_the_requested_currency(session: Session) -> None:
    result = run(
        session,
        {
            "kind": "aggregate",
            "filters": [{"field": "country", "op": "eq", "value": SAMPLE.country}],
            "measures": [{"name": "payroll", "function": "sum", "field": "salary"}],
            "currency": "INR",
        },
    )

    total = sum((usd(e) for e in where(lambda e: e.country == SAMPLE.country)), Decimal(0))
    assert scalar(result, "payroll") == cents(total / RATES["INR"])
    assert result.columns[0].currency == "INR"


def test_converting_back_to_the_local_currency_is_exact(session: Session) -> None:
    country = SAMPLE.country
    local = [e for e in EMPLOYEES if e.country == country]
    currency = local[0].currency_code
    result = run(
        session,
        {
            "kind": "aggregate",
            "filters": [{"field": "country", "op": "eq", "value": country}],
            "measures": [{"name": "average", "function": "avg", "field": "salary"}],
            "currency": currency,
        },
    )

    assert scalar(result, "average") == cents(
        sum((e.annual_salary for e in local), Decimal(0)) / len(local)
    )


def test_empty_selection_gives_zero_counts_and_no_averages(session: Session) -> None:
    result = run(
        session,
        {
            "kind": "aggregate",
            "filters": [{"field": "salary", "op": "lt", "value": 0}],
            "measures": [
                {"name": "n", "function": "count"},
                {"name": "payroll", "function": "sum", "field": "salary"},
                {"name": "average", "function": "avg", "field": "salary"},
                {"name": "middle", "function": "median", "field": "salary"},
            ],
            "calculations": [{"name": "share", "op": "percent", "left": "n", "right": "n"}],
        },
    )

    assert scalar(result, "n") == 0
    assert scalar(result, "payroll") == Decimal("0.00")
    assert scalar(result, "average") is None
    assert scalar(result, "middle") is None
    # Dividing by an empty count is undefined rather than an error.
    assert scalar(result, "share") is None


def test_employee_without_compensation_counts_but_has_no_salary(session: Session) -> None:
    session.execute(
        insert(Employee).values(
            employee_code="EMP99999",
            full_name="Zed Unpaid",
            country=SAMPLE.country,
            department=SAMPLE.department,
            job_title=SAMPLE.job_title,
        )
    )
    session.commit()

    totals = run(
        session,
        {
            "kind": "aggregate",
            "measures": [
                {"name": "employees", "function": "count"},
                {"name": "paid", "function": "count", "field": "salary"},
                {"name": "payroll", "function": "sum", "field": "salary"},
            ],
        },
    )
    rows = run(
        session,
        {
            "kind": "rows",
            "filters": [{"field": "employee_code", "op": "eq", "value": "EMP99999"}],
            "fields": ["full_name", "salary", "currency"],
        },
    )

    assert scalar(totals, "employees") == len(EMPLOYEES) + 1
    assert scalar(totals, "paid") == len(EMPLOYEES)
    assert scalar(totals, "payroll") == cents(sum((usd(e) for e in EMPLOYEES), Decimal(0)))
    assert [row.values for row in rows.rows] == [("Zed Unpaid", None, None)]


def test_query_values_are_bound_not_interpolated(session: Session) -> None:
    injection = "x'; DELETE FROM compensation; --"
    result = run(
        session,
        {
            "kind": "rows",
            "filters": [{"field": "full_name", "op": "contains", "value": injection}],
            "fields": ["full_name"],
        },
    )

    assert result.rows == ()
    count = run(session, {"kind": "aggregate", "measures": [{"name": "n", "function": "count"}]})
    assert scalar(count, "n") == len(EMPLOYEES)


def test_ask_transactions_are_read_only(session: Session) -> None:
    begin_read_only(session)
    run(session, {"kind": "aggregate", "measures": [{"name": "n", "function": "count"}]})

    with pytest.raises(InternalError, match="read-only transaction"):
        session.execute(update(Compensation).values(annual_salary=Compensation.annual_salary + 1))
    session.rollback()
