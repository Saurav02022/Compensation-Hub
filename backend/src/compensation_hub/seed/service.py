from dataclasses import dataclass

from sqlalchemy import func, insert, select, text
from sqlalchemy.orm import Session

from compensation_hub.db.base import Base
from compensation_hub.db.models import Compensation, Employee, FxRate
from compensation_hub.seed.dataset import SeedDataset


@dataclass(frozen=True)
class SeedResult:
    employee_count: int
    fx_rate_count: int


class DatabaseAlreadySeededError(Exception):
    """Raised when seed data exists and the caller did not ask for a reset."""


def seed_database(session: Session, dataset: SeedDataset, *, reset: bool = False) -> SeedResult:
    """Load the dataset in one transaction.

    Refuses to run on a non-empty database unless ``reset`` is set, in which case all
    MVP tables are truncated first so a reseed always yields the same rows.
    """
    existing_employees = session.scalar(select(func.count()).select_from(Employee)) or 0
    if existing_employees and not reset:
        raise DatabaseAlreadySeededError(
            f"Database already contains {existing_employees} employees; use reset to reseed."
        )

    if reset:
        table_names = ", ".join(table.name for table in Base.metadata.sorted_tables)
        session.execute(text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY"))

    session.execute(
        insert(FxRate),
        [
            {"currency_code": rate.currency_code, "rate_to_usd": rate.rate_to_usd}
            for rate in dataset.fx_rates
        ],
    )
    session.execute(
        insert(Employee),
        [
            {
                "employee_code": employee.employee_code,
                "full_name": employee.full_name,
                "country": employee.country,
                "department": employee.department,
                "job_title": employee.job_title,
            }
            for employee in dataset.employees
        ],
    )
    employee_ids: dict[str, int] = {
        code: employee_id
        for code, employee_id in session.execute(select(Employee.employee_code, Employee.id))
    }
    session.execute(
        insert(Compensation),
        [
            {
                "employee_id": employee_ids[employee.employee_code],
                "annual_salary": employee.annual_salary,
                "currency_code": employee.currency_code,
            }
            for employee in dataset.employees
        ],
    )
    session.commit()

    return SeedResult(employee_count=len(dataset.employees), fx_rate_count=len(dataset.fx_rates))
