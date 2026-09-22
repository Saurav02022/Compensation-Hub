from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from compensation_hub.db.models import Compensation, Employee


def employee_id_for(session: Session, employee_code: str) -> int:
    employee_id = session.scalar(select(Employee.id).where(Employee.employee_code == employee_code))
    assert employee_id is not None
    return employee_id


def test_update_salary_persists_exact_decimal(
    seeded_client: TestClient, db_session: Session
) -> None:
    employee_id = employee_id_for(db_session, "EMP00001")

    response = seeded_client.patch(
        f"/employees/{employee_id}/compensation",
        json={"annual_salary": "123456.78", "currency_code": "USD"},
    )

    assert response.status_code == 200
    assert response.json() == {"annual_salary": "123456.78", "currency_code": "USD"}

    db_session.expire_all()
    stored = db_session.get(Compensation, employee_id)
    assert stored is not None
    assert stored.annual_salary == Decimal("123456.78")
    assert stored.currency_code == "USD"

    detail = seeded_client.get(f"/employees/{employee_id}").json()
    assert detail["compensation"] == {"annual_salary": "123456.78", "currency_code": "USD"}


def test_update_accepts_supported_currency_change(
    seeded_client: TestClient, db_session: Session
) -> None:
    employee_id = employee_id_for(db_session, "EMP00001")

    response = seeded_client.patch(
        f"/employees/{employee_id}/compensation",
        json={"annual_salary": "2400000", "currency_code": "INR"},
    )

    assert response.status_code == 200
    assert response.json() == {"annual_salary": "2400000.00", "currency_code": "INR"}


@pytest.mark.parametrize(
    "annual_salary",
    ["0", "-1", "12.345", "abc", "1e20", None],
)
def test_update_rejects_invalid_salary(
    seeded_client: TestClient, db_session: Session, annual_salary: str | None
) -> None:
    employee_id = employee_id_for(db_session, "EMP00001")
    original = seeded_client.get(f"/employees/{employee_id}").json()["compensation"]

    response = seeded_client.patch(
        f"/employees/{employee_id}/compensation",
        json={"annual_salary": annual_salary, "currency_code": "USD"},
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "annual_salary"]
    assert seeded_client.get(f"/employees/{employee_id}").json()["compensation"] == original


def test_update_rejects_unsupported_currency(
    seeded_client: TestClient, db_session: Session
) -> None:
    employee_id = employee_id_for(db_session, "EMP00001")
    original = seeded_client.get(f"/employees/{employee_id}").json()["compensation"]

    response = seeded_client.patch(
        f"/employees/{employee_id}/compensation",
        json={"annual_salary": "50000", "currency_code": "XYZ"},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Currency XYZ is not supported"}
    assert seeded_client.get(f"/employees/{employee_id}").json()["compensation"] == original


@pytest.mark.parametrize("currency_code", ["usd", "US", "USDX", ""])
def test_update_rejects_malformed_currency_code(
    seeded_client: TestClient, db_session: Session, currency_code: str
) -> None:
    employee_id = employee_id_for(db_session, "EMP00001")

    response = seeded_client.patch(
        f"/employees/{employee_id}/compensation",
        json={"annual_salary": "50000", "currency_code": currency_code},
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "currency_code"]


def test_update_requires_both_fields(seeded_client: TestClient, db_session: Session) -> None:
    employee_id = employee_id_for(db_session, "EMP00001")

    missing_currency = seeded_client.patch(
        f"/employees/{employee_id}/compensation", json={"annual_salary": "50000"}
    )
    missing_salary = seeded_client.patch(
        f"/employees/{employee_id}/compensation", json={"currency_code": "USD"}
    )

    assert missing_currency.status_code == 422
    assert missing_salary.status_code == 422


def test_update_rejects_unknown_fields(seeded_client: TestClient, db_session: Session) -> None:
    employee_id = employee_id_for(db_session, "EMP00001")

    response = seeded_client.patch(
        f"/employees/{employee_id}/compensation",
        json={"annual_salary": "50000", "currency_code": "USD", "full_name": "Someone Else"},
    )

    assert response.status_code == 422


def test_update_missing_employee_returns_404(seeded_client: TestClient) -> None:
    response = seeded_client.patch(
        "/employees/999999/compensation",
        json={"annual_salary": "50000", "currency_code": "USD"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Employee 999999 not found"}


def test_update_creates_compensation_when_employee_has_none(
    seeded_client: TestClient, db_session: Session
) -> None:
    employee = Employee(
        employee_code="EMP99999",
        full_name="No Pay Yet",
        country="United States",
        department="Finance",
        job_title="Accountant",
    )
    db_session.add(employee)
    db_session.commit()

    response = seeded_client.patch(
        f"/employees/{employee.id}/compensation",
        json={"annual_salary": "70000.00", "currency_code": "USD"},
    )

    assert response.status_code == 200
    assert seeded_client.get(f"/employees/{employee.id}").json()["compensation"] == {
        "annual_salary": "70000.00",
        "currency_code": "USD",
    }
