from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from compensation_hub.db.models import Compensation, Employee, FxRate
from compensation_hub.seed.dataset import build_seed_dataset
from compensation_hub.seed.service import DatabaseAlreadySeededError, seed_database


def stored_rows(session: Session) -> list[tuple[str, str, str, str, str, Decimal, str]]:
    statement = (
        select(
            Employee.employee_code,
            Employee.full_name,
            Employee.country,
            Employee.department,
            Employee.job_title,
            Compensation.annual_salary,
            Compensation.currency_code,
        )
        .join(Compensation, Compensation.employee_id == Employee.id)
        .order_by(Employee.employee_code)
    )
    return [tuple(row) for row in session.execute(statement)]


def test_seed_populates_clean_database_with_complete_dataset(db_session: Session) -> None:
    dataset = build_seed_dataset()

    result = seed_database(db_session, dataset)

    assert result.employee_count == 10_000
    assert db_session.scalar(select(func.count()).select_from(Employee)) == 10_000
    assert db_session.scalar(select(func.count()).select_from(Compensation)) == 10_000
    assert db_session.scalar(select(func.count()).select_from(FxRate)) == len(dataset.fx_rates)

    expected = [
        (
            employee.employee_code,
            employee.full_name,
            employee.country,
            employee.department,
            employee.job_title,
            employee.annual_salary,
            employee.currency_code,
        )
        for employee in dataset.employees
    ]
    assert stored_rows(db_session) == expected


def test_seed_refuses_to_run_on_populated_database(db_session: Session) -> None:
    dataset = build_seed_dataset(employee_count=20)
    seed_database(db_session, dataset)

    with pytest.raises(DatabaseAlreadySeededError):
        seed_database(db_session, dataset)

    assert db_session.scalar(select(func.count()).select_from(Employee)) == 20


def test_reset_reseeds_identical_data(db_session: Session) -> None:
    dataset = build_seed_dataset(employee_count=200)
    seed_database(db_session, dataset)
    first_rows = stored_rows(db_session)

    changed = db_session.scalars(select(Compensation).limit(1)).one()
    changed.annual_salary = Decimal("1.00")
    db_session.commit()

    seed_database(db_session, dataset, reset=True)

    assert stored_rows(db_session) == first_rows
    assert db_session.scalar(select(func.count()).select_from(Employee)) == 200
