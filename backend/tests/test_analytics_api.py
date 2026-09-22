from collections import defaultdict
from collections.abc import Callable
from decimal import ROUND_HALF_UP, Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from compensation_hub.analytics.service import AnalyticsFilters, MissingFxRateError, get_summary
from compensation_hub.db.models import Employee
from compensation_hub.seed.dataset import SeedEmployee, build_seed_dataset

DATASET = build_seed_dataset(employee_count=60)
RATES = {rate.currency_code: rate.rate_to_usd for rate in DATASET.fx_rates}
CENTS = Decimal("0.01")


def usd(employee: SeedEmployee) -> Decimal:
    return employee.annual_salary * RATES[employee.currency_code]


def money(value: Decimal) -> str:
    return str(value.quantize(CENTS, rounding=ROUND_HALF_UP))


def expected_metrics(employees: list[SeedEmployee]) -> dict[str, object]:
    total = sum((usd(e) for e in employees), Decimal(0))
    return {
        "employee_count": len(employees),
        "total_payroll_usd": money(total),
        "average_salary_usd": money(total / len(employees)) if employees else None,
    }


def expected_breakdown(
    employees: list[SeedEmployee], key: Callable[[SeedEmployee], str]
) -> list[dict[str, object]]:
    groups: dict[str, list[SeedEmployee]] = defaultdict(list)
    for employee in employees:
        groups[key(employee)].append(employee)
    return [{"key": name, **expected_metrics(groups[name])} for name in sorted(groups)]


def test_summary_normalizes_payroll_to_usd(seeded_client: TestClient) -> None:
    response = seeded_client.get("/analytics/summary")

    assert response.status_code == 200
    assert response.json() == {"currency": "USD", **expected_metrics(list(DATASET.employees))}


def test_summary_applies_filters(seeded_client: TestClient) -> None:
    sample = DATASET.employees[0]
    matching = [
        e
        for e in DATASET.employees
        if e.country == sample.country and e.department == sample.department
    ]

    body = seeded_client.get(
        "/analytics/summary", params={"country": sample.country, "department": sample.department}
    ).json()

    assert body == {"currency": "USD", **expected_metrics(matching)}


def test_summary_with_no_matching_employees_has_zero_payroll_and_no_average(
    seeded_client: TestClient,
) -> None:
    body = seeded_client.get("/analytics/summary", params={"country": "Atlantis"}).json()

    assert body == {
        "currency": "USD",
        "employee_count": 0,
        "total_payroll_usd": "0.00",
        "average_salary_usd": None,
    }


def test_summary_counts_employees_without_compensation_but_excludes_them_from_money(
    seeded_client: TestClient, db_session: Session
) -> None:
    db_session.add(
        Employee(
            employee_code="EMP99999",
            full_name="No Pay Yet",
            country="Atlantis",
            department="Finance",
            job_title="Accountant",
        )
    )
    db_session.commit()

    body = seeded_client.get("/analytics/summary", params={"country": "Atlantis"}).json()

    assert body["employee_count"] == 1
    assert body["total_payroll_usd"] == "0.00"
    assert body["average_salary_usd"] is None


@pytest.mark.parametrize(
    ("group_by", "key"),
    [
        ("country", lambda e: e.country),
        ("department", lambda e: e.department),
        ("job_title", lambda e: e.job_title),
    ],
)
def test_breakdown_groups_by_each_supported_dimension(
    seeded_client: TestClient, group_by: str, key: Callable[[SeedEmployee], str]
) -> None:
    response = seeded_client.get("/analytics/breakdown", params={"group_by": group_by})

    assert response.status_code == 200
    body = response.json()
    assert body["group_by"] == group_by
    assert body["currency"] == "USD"
    assert body["rows"] == expected_breakdown(list(DATASET.employees), key)


def test_breakdown_applies_filters(seeded_client: TestClient) -> None:
    sample = DATASET.employees[0]
    matching = [e for e in DATASET.employees if e.department == sample.department]

    body = seeded_client.get(
        "/analytics/breakdown", params={"group_by": "country", "department": sample.department}
    ).json()

    assert body["rows"] == expected_breakdown(matching, lambda e: e.country)


def test_breakdown_sorts_by_metric_and_limits_rows(seeded_client: TestClient) -> None:
    all_rows = expected_breakdown(list(DATASET.employees), lambda e: e.department)
    by_payroll = sorted(
        all_rows, key=lambda r: (-Decimal(str(r["total_payroll_usd"])), str(r["key"]))
    )

    body = seeded_client.get(
        "/analytics/breakdown",
        params={
            "group_by": "department",
            "sort_by": "total_payroll_usd",
            "descending": "true",
            "limit": 3,
        },
    ).json()

    assert body["rows"] == by_payroll[:3]


def test_breakdown_sorts_by_employee_count_ascending_with_key_tiebreak(
    seeded_client: TestClient,
) -> None:
    all_rows = expected_breakdown(list(DATASET.employees), lambda e: e.country)
    by_count = sorted(all_rows, key=lambda r: (int(str(r["employee_count"])), str(r["key"])))

    body = seeded_client.get(
        "/analytics/breakdown", params={"group_by": "country", "sort_by": "employee_count"}
    ).json()

    assert body["rows"] == by_count


def test_breakdown_returns_no_rows_when_nothing_matches(seeded_client: TestClient) -> None:
    body = seeded_client.get(
        "/analytics/breakdown", params={"group_by": "country", "department": "Astrology"}
    ).json()

    assert body["rows"] == []


def test_breakdown_rejects_unsupported_parameters(seeded_client: TestClient) -> None:
    assert seeded_client.get("/analytics/breakdown").status_code == 422
    assert (
        seeded_client.get("/analytics/breakdown", params={"group_by": "salary"}).status_code == 422
    )
    assert (
        seeded_client.get(
            "/analytics/breakdown", params={"group_by": "country", "sort_by": "name"}
        ).status_code
        == 422
    )
    assert (
        seeded_client.get(
            "/analytics/breakdown", params={"group_by": "country", "limit": 0}
        ).status_code
        == 422
    )
    assert (
        seeded_client.get(
            "/analytics/breakdown", params={"group_by": "country", "limit": 101}
        ).status_code
        == 422
    )


def test_missing_fx_rate_is_an_error_rather_than_a_silent_exclusion(
    seeded_client: TestClient, db_session: Session
) -> None:
    # The foreign key normally makes this state unreachable; it is lifted here only to
    # prove the analytics layer refuses to compute with an unknown exchange rate.
    db_session.execute(
        text("ALTER TABLE compensation DROP CONSTRAINT fk_compensation_currency_code_fx_rates")
    )
    db_session.execute(text("UPDATE compensation SET currency_code = 'XXX' WHERE employee_id = 1"))
    db_session.commit()
    try:
        with pytest.raises(MissingFxRateError) as raised:
            get_summary(db_session, AnalyticsFilters())
        assert raised.value.currency_codes == ("XXX",)

        response = seeded_client.get("/analytics/summary")
        assert response.status_code == 500
        assert response.json() == {"detail": "No exchange rate is configured for currency XXX"}
    finally:
        db_session.execute(
            text("UPDATE compensation SET currency_code = 'USD' WHERE employee_id = 1")
        )
        db_session.execute(
            text(
                "ALTER TABLE compensation ADD CONSTRAINT fk_compensation_currency_code_fx_rates "
                "FOREIGN KEY (currency_code) REFERENCES fx_rates (currency_code) ON DELETE RESTRICT"
            )
        )
        db_session.commit()
