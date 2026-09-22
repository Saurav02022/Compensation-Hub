from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from compensation_hub.db.models import Compensation, Employee, FxRate


def make_employee(code: str = "EMP00001") -> Employee:
    return Employee(
        employee_code=code,
        full_name="Test Person",
        country="United States",
        department="Engineering",
        job_title="Software Engineer",
    )


@pytest.fixture
def usd_rate(db_session: Session) -> FxRate:
    rate = FxRate(currency_code="USD", rate_to_usd=Decimal("1"))
    db_session.add(rate)
    db_session.commit()
    return rate


def test_employee_code_must_be_unique(db_session: Session) -> None:
    db_session.add(make_employee("EMP00001"))
    db_session.commit()

    db_session.add(make_employee("EMP00001"))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_employee_can_have_only_one_compensation_record(
    db_session: Session, usd_rate: FxRate
) -> None:
    employee = make_employee()
    db_session.add(employee)
    db_session.commit()

    db_session.add(
        Compensation(employee_id=employee.id, annual_salary=Decimal("100000"), currency_code="USD")
    )
    db_session.commit()

    db_session.add(
        Compensation(employee_id=employee.id, annual_salary=Decimal("120000"), currency_code="USD")
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


@pytest.mark.parametrize("salary", [Decimal("0"), Decimal("-1500.00")])
def test_annual_salary_must_be_positive(
    db_session: Session, usd_rate: FxRate, salary: Decimal
) -> None:
    employee = make_employee()
    db_session.add(employee)
    db_session.commit()

    db_session.add(Compensation(employee_id=employee.id, annual_salary=salary, currency_code="USD"))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_compensation_currency_must_have_an_fx_rate(db_session: Session) -> None:
    employee = make_employee()
    db_session.add(employee)
    db_session.commit()

    db_session.add(
        Compensation(employee_id=employee.id, annual_salary=Decimal("100000"), currency_code="XXX")
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_fx_rate_in_use_cannot_be_deleted(db_session: Session, usd_rate: FxRate) -> None:
    employee = make_employee()
    db_session.add(employee)
    db_session.commit()
    db_session.add(
        Compensation(employee_id=employee.id, annual_salary=Decimal("100000"), currency_code="USD")
    )
    db_session.commit()

    db_session.delete(usd_rate)
    with pytest.raises(IntegrityError):
        db_session.commit()


@pytest.mark.parametrize("code", ["usd", "US", "1AB"])
def test_fx_rate_currency_code_must_be_three_uppercase_letters(
    db_session: Session, code: str
) -> None:
    db_session.add(FxRate(currency_code=code, rate_to_usd=Decimal("1")))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_fx_rate_must_be_positive(db_session: Session) -> None:
    db_session.add(FxRate(currency_code="EUR", rate_to_usd=Decimal("0")))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_deleting_employee_removes_its_compensation(db_session: Session, usd_rate: FxRate) -> None:
    employee = make_employee()
    db_session.add(employee)
    db_session.commit()
    db_session.add(
        Compensation(employee_id=employee.id, annual_salary=Decimal("100000"), currency_code="USD")
    )
    db_session.commit()

    db_session.delete(employee)
    db_session.commit()

    assert db_session.get(Compensation, employee.id) is None


def test_monetary_values_round_trip_as_exact_decimals(
    db_session: Session, usd_rate: FxRate
) -> None:
    employee = make_employee()
    db_session.add(employee)
    db_session.commit()
    db_session.add(
        Compensation(
            employee_id=employee.id, annual_salary=Decimal("123456.78"), currency_code="USD"
        )
    )
    db_session.commit()
    db_session.expire_all()

    stored = db_session.get(Compensation, employee.id)
    assert stored is not None
    assert stored.annual_salary == Decimal("123456.78")
    assert isinstance(stored.annual_salary, Decimal)
