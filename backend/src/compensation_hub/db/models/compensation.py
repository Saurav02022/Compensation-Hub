from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from compensation_hub.db.base import Base

if TYPE_CHECKING:
    from compensation_hub.db.models.employee import Employee
    from compensation_hub.db.models.fx_rate import FxRate


class Compensation(Base):
    """Current annual compensation for one employee, stored in the employee's local currency."""

    __tablename__ = "compensation"
    __table_args__ = (CheckConstraint("annual_salary > 0", name="annual_salary_positive"),)

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), primary_key=True
    )
    annual_salary: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency_code: Mapped[str] = mapped_column(
        String(3), ForeignKey("fx_rates.currency_code", ondelete="RESTRICT")
    )

    employee: Mapped[Employee] = relationship(back_populates="compensation")
    fx_rate: Mapped[FxRate] = relationship()
