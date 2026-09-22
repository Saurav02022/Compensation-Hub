from decimal import Decimal

from sqlalchemy.orm import Session

from compensation_hub.db.models import Compensation, FxRate
from compensation_hub.employees.service import get_employee


class UnsupportedCurrencyError(Exception):
    def __init__(self, currency_code: str) -> None:
        super().__init__(f"Currency {currency_code} is not supported")
        self.currency_code = currency_code


def update_compensation(
    session: Session, employee_id: int, annual_salary: Decimal, currency_code: str
) -> Compensation:
    """Replace the employee's current compensation.

    A currency is supported only when a seeded FX rate exists for it, which guarantees
    the new salary can be normalized for organization-wide analytics.
    """
    employee = get_employee(session, employee_id)

    if session.get(FxRate, currency_code) is None:
        raise UnsupportedCurrencyError(currency_code)

    compensation = employee.compensation
    if compensation is None:
        compensation = Compensation(employee_id=employee.id)
        session.add(compensation)

    compensation.annual_salary = annual_salary
    compensation.currency_code = currency_code
    session.commit()
    session.refresh(compensation)
    return compensation
