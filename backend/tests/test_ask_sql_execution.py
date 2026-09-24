"""Validated SQL run against PostgreSQL, with expected values computed independently.

Expected figures come from the seed dataset in Decimal arithmetic, and common questions are
compared with the Analytics service, so these tests show that the controlled SQL path answers
relational questions correctly rather than matching a list of anticipated questions.
"""

from collections import defaultdict
from collections.abc import Callable
from decimal import ROUND_HALF_UP, Decimal

import pytest
from sqlalchemy import insert, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from compensation_hub.analytics.service import AnalyticsFilters, get_breakdown, get_summary
from compensation_hub.ask_compensation.execution import (
    QueryResult,
    begin_read_only,
    execute_sql,
)
from compensation_hub.ask_compensation.sql_validation import MAX_ROWS, validate_sql
from compensation_hub.db.models import Employee
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
    return ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2


def where(predicate: Callable[[SeedEmployee], bool]) -> list[SeedEmployee]:
    return [employee for employee in EMPLOYEES if predicate(employee)]


@pytest.fixture
def session(db_session: Session) -> Session:
    seed_database(db_session, DATASET)
    db_session.commit()
    return db_session


def run(
    session: Session,
    sql: str,
    currency: str = "USD",
    percent: frozenset[str] = frozenset(),
) -> QueryResult:
    begin_read_only(session)
    try:
        return execute_sql(session, validate_sql(sql, percent), currency, RATES[currency])
    finally:
        session.rollback()


def scalar(result: QueryResult, key: str | None = None) -> object:
    assert len(result.rows) == 1
    index = 0 if key is None else [column.key for column in result.columns].index(key)
    return result.rows[0].values[index]


def column(result: QueryResult, key: str) -> list[object]:
    index = [column.key for column in result.columns].index(key)
    return [row.values[index] for row in result.rows]


def test_headcount_matches_the_analytics_summary(session: Session) -> None:
    result = run(
        session,
        f"SELECT COUNT(*) AS employees FROM employees WHERE department = '{SAMPLE.department}'",
    )

    summary = get_summary(session, AnalyticsFilters(department=SAMPLE.department))
    assert scalar(result) == summary.employee_count
    assert result.columns[0].type == "count"


def test_grouped_payroll_and_average_match_the_analytics_breakdown(session: Session) -> None:
    result = run(
        session,
        "SELECT department, COUNT(*) AS employees, SUM(salary_usd) AS payroll, "
        "AVG(salary_usd) AS average FROM employees GROUP BY department ORDER BY department",
    )

    breakdown = get_breakdown(session, "department", AnalyticsFilters())
    assert [row.values for row in result.rows] == [
        (row.key, row.employee_count, row.total_payroll_usd, row.average_salary_usd)
        for row in breakdown
    ]
    assert [c.type for c in result.columns] == ["text", "count", "money", "money"]


def test_employee_lookup_links_rows_and_keeps_local_currency(session: Session) -> None:
    result = run(
        session,
        "SELECT employee_id, full_name, salary_local, salary_currency FROM employees "
        f"WHERE employee_code = '{SAMPLE.employee_code}'",
    )

    assert [c.key for c in result.columns] == ["full_name", "salary_local", "salary_currency"]
    assert result.rows[0].values == (SAMPLE.full_name, SAMPLE.annual_salary, SAMPLE.currency_code)
    assert result.rows[0].employee_id == 1
    assert result.columns[1].currency_key == "salary_currency"


def test_ranking_by_normalized_salary(session: Session) -> None:
    result = run(
        session,
        "SELECT full_name, salary_usd FROM employees ORDER BY salary_usd DESC, full_name LIMIT 5",
    )

    top = sorted(EMPLOYEES, key=lambda e: (-usd(e), e.full_name))[:5]
    assert column(result, "full_name") == [e.full_name for e in top]
    assert column(result, "salary_usd") == [cents(usd(e)) for e in top]


def test_min_max_and_exact_median(session: Session) -> None:
    result = run(
        session,
        "SELECT MIN(salary_usd) AS lowest, MAX(salary_usd) AS highest, "
        "PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY salary_usd) AS middle FROM employees",
    )

    salaries = [usd(e) for e in EMPLOYEES]
    assert scalar(result, "lowest") == cents(min(salaries))
    assert scalar(result, "highest") == cents(max(salaries))
    assert scalar(result, "middle") == cents(median(salaries))


def test_median_of_an_odd_filtered_group(session: Session) -> None:
    top = max(usd(e) for e in EMPLOYEES)
    result = run(
        session,
        f"SELECT MEDIAN(salary_usd) FILTER (WHERE salary_usd < {top}) AS middle FROM employees",
    )

    salaries = [usd(e) for e in EMPLOYEES if usd(e) < top]
    assert len(salaries) % 2 == 1
    assert scalar(result) == cents(median(salaries))


def test_percentage_with_exact_division(session: Session) -> None:
    result = run(
        session,
        "SELECT COUNT(*) FILTER (WHERE country = 'India') * 100 / COUNT(*) AS share "
        f"FROM employees WHERE department = '{SAMPLE.department}'",
        percent=frozenset({"share"}),
    )

    members = where(lambda e: e.department == SAMPLE.department)
    india = sum(1 for e in members if e.country == "India")
    assert scalar(result) == cents(Decimal(india) * 100 / len(members))
    assert result.columns[0].type == "percent"


def test_share_of_payroll(session: Session) -> None:
    result = run(
        session,
        "SELECT SUM(salary_usd) FILTER (WHERE department = 'Engineering') * 100 "
        "/ SUM(salary_usd) AS share FROM employees",
        percent=frozenset({"share"}),
    )

    total = sum((usd(e) for e in EMPLOYEES), Decimal(0))
    engineering = sum((usd(e) for e in where(lambda e: e.department == "Engineering")), Decimal(0))
    assert scalar(result) == cents(engineering * 100 / total)


def test_distinct_values(session: Session) -> None:
    result = run(session, "SELECT DISTINCT salary_currency FROM employees ORDER BY 1")

    assert column(result, "salary_currency") == sorted({e.currency_code for e in EMPLOYEES})


def test_cross_country_comparison_in_another_currency(session: Session) -> None:
    first, second = sorted({e.country for e in EMPLOYEES})[:2]
    result = run(
        session,
        f"SELECT SUM(salary_usd) FILTER (WHERE country = '{first}') - "
        f"SUM(salary_usd) FILTER (WHERE country = '{second}') AS difference FROM employees",
        currency="INR",
    )

    a = sum((usd(e) for e in where(lambda e: e.country == first)), Decimal(0))
    b = sum((usd(e) for e in where(lambda e: e.country == second)), Decimal(0))
    assert scalar(result) == cents((a - b) / RATES["INR"])
    assert result.columns[0].currency == "INR"


def test_converting_back_to_the_local_currency_is_exact(session: Session) -> None:
    local = where(lambda e: e.country == SAMPLE.country)
    result = run(
        session,
        f"SELECT AVG(salary_usd) AS average FROM employees WHERE country = '{SAMPLE.country}'",
        currency=local[0].currency_code,
    )

    total = sum((e.annual_salary for e in local), Decimal(0))
    assert scalar(result) == cents(total / len(local))


def test_threshold_in_another_currency_uses_the_seeded_rate(session: Session) -> None:
    result = run(
        session,
        "SELECT COUNT(*) AS n FROM employees WHERE salary_usd > 5000000 * "
        "(SELECT rate_to_usd FROM fx_rates WHERE currency_code = 'INR')",
    )

    threshold = Decimal(5000000) * RATES["INR"]
    assert scalar(result) == len(where(lambda e: usd(e) > threshold))


def test_or_conditions(session: Session) -> None:
    result = run(
        session,
        "SELECT COUNT(*) AS n FROM employees WHERE country = 'India' "
        "OR (department = 'Sales' AND country = 'Germany')",
    )

    expected = where(
        lambda e: e.country == "India" or (e.department == "Sales" and e.country == "Germany")
    )
    assert scalar(result) == len(expected)


def test_group_relative_subquery(session: Session) -> None:
    result = run(
        session,
        "SELECT COUNT(*) AS above FROM employees AS e WHERE salary_usd > "
        "(SELECT AVG(salary_usd) FROM employees AS d WHERE d.department = e.department)",
    )

    averages: dict[str, list[Decimal]] = defaultdict(list)
    for employee in EMPLOYEES:
        averages[employee.department].append(usd(employee))
    expected = where(
        lambda e: usd(e) > sum(averages[e.department], Decimal(0)) / len(averages[e.department])
    )
    assert scalar(result) == len(expected)


def test_cte_with_join(session: Session) -> None:
    result = run(
        session,
        "WITH d AS (SELECT department, MAX(salary_usd) - MIN(salary_usd) AS gap "
        "FROM employees GROUP BY department) SELECT department, gap FROM d "
        "ORDER BY gap DESC, department LIMIT 3",
    )

    salaries: dict[str, list[Decimal]] = defaultdict(list)
    for employee in EMPLOYEES:
        salaries[employee.department].append(usd(employee))
    gaps = sorted(((max(v) - min(v), k) for k, v in salaries.items()), key=lambda g: (-g[0], g[1]))
    assert [row.values for row in result.rows] == [(k, cents(g)) for g, k in gaps[:3]]


def test_window_ranking_per_group(session: Session) -> None:
    result = run(
        session,
        "SELECT country, full_name FROM (SELECT country, full_name, ROW_NUMBER() OVER "
        "(PARTITION BY country ORDER BY salary_usd DESC, full_name) AS position "
        "FROM employees) AS ranked WHERE position = 1 ORDER BY country",
    )

    best: dict[str, SeedEmployee] = {}
    for employee in sorted(EMPLOYEES, key=lambda e: (-usd(e), e.full_name)):
        best.setdefault(employee.country, employee)
    assert [row.values for row in result.rows] == [
        (country, best[country].full_name) for country in sorted(best)
    ]


def test_employee_without_compensation(session: Session) -> None:
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

    result = run(
        session,
        "SELECT COUNT(*) AS employees, COUNT(salary_usd) AS paid, SUM(salary_usd) AS payroll "
        "FROM employees",
    )
    unpaid = run(
        session,
        "SELECT full_name, salary_usd FROM employees WHERE salary_usd IS NULL",
    )

    assert result.rows[0].values == (
        len(EMPLOYEES) + 1,
        len(EMPLOYEES),
        cents(sum((usd(e) for e in EMPLOYEES), Decimal(0))),
    )
    assert [row.values for row in unpaid.rows] == [("Zed Unpaid", None)]


def test_empty_results_and_nulls(session: Session) -> None:
    empty = run(session, "SELECT full_name FROM employees WHERE country = 'Atlantis'")
    aggregate = run(
        session,
        "SELECT COUNT(*) AS n, SUM(salary_usd) AS total, AVG(salary_usd) AS average "
        "FROM employees WHERE country = 'Atlantis'",
    )

    assert empty.rows == () and empty.total_rows == 0
    assert aggregate.rows[0].values == (0, None, None)


def test_literal_values_with_wildcards_and_quotes_are_bound(session: Session) -> None:
    sql = (
        "SELECT COUNT(*) AS n FROM employees WHERE full_name = '100%' "
        "OR full_name LIKE '%:name%' OR full_name = 'x''; DROP TABLE employees; --' "
        "OR full_name = 'a_b' OR full_name = 'back\\slash' OR full_name = 'x; SELECT 1'"
    )
    validated = validate_sql(sql)
    result = run(session, sql)

    assert set(validated.parameters.values()) == {
        "100%",
        "%:name%",
        "x'; DROP TABLE employees; --",
        "a_b",
        "back\\slash",
        "x; SELECT 1",
    }
    assert "DROP" not in validated.executable and "slash" not in validated.executable
    assert scalar(result) == 0
    assert session.scalar(text("SELECT COUNT(*) FROM employees")) == len(EMPLOYEES)


def test_division_by_zero_yields_no_value(session: Session) -> None:
    result = run(
        session,
        "SELECT SUM(salary_usd) / COUNT(*) FILTER (WHERE country = 'Atlantis') AS per_head "
        "FROM employees",
    )

    assert scalar(result) is None


def test_results_are_capped_and_report_the_total(session: Session) -> None:
    extra = [
        {
            "employee_code": f"EMP9{index:04d}",
            "full_name": f"Extra {index:03d}",
            "country": SAMPLE.country,
            "department": SAMPLE.department,
            "job_title": SAMPLE.job_title,
        }
        for index in range(MAX_ROWS)
    ]
    session.execute(insert(Employee), extra)
    session.commit()

    result = run(session, "SELECT full_name FROM employees ORDER BY full_name")
    # A LIMIT at the cap is the model's way of asking for "as many as can be shown".
    limited = run(session, f"SELECT full_name FROM employees ORDER BY full_name LIMIT {MAX_ROWS}")

    assert len(result.rows) == MAX_ROWS
    assert result.total_rows == len(EMPLOYEES) + MAX_ROWS
    assert limited.rows == result.rows
    assert limited.total_rows == len(EMPLOYEES) + MAX_ROWS


def test_the_transaction_refuses_writes(session: Session) -> None:
    begin_read_only(session)
    execute_sql(session, validate_sql("SELECT COUNT(*) AS n FROM employees"), "USD", Decimal(1))

    with pytest.raises(DBAPIError, match="read-only transaction"):
        session.execute(text("UPDATE compensation SET annual_salary = annual_salary + 1"))
    session.rollback()


def test_statement_timeout_applies(session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("compensation_hub.ask_compensation.execution.STATEMENT_TIMEOUT", "1ms")
    heavy = validate_sql(
        "SELECT COUNT(*) AS n FROM employees AS a CROSS JOIN employees AS b "
        "CROSS JOIN employees AS c CROSS JOIN employees AS d"
    )

    begin_read_only(session)
    with pytest.raises(DBAPIError) as raised:
        execute_sql(session, heavy, "USD", Decimal(1))
    session.rollback()

    assert getattr(raised.value.orig, "sqlstate", None) == "57014"
