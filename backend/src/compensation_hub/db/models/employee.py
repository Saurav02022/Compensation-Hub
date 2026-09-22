from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Identity, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from compensation_hub.db.base import Base

if TYPE_CHECKING:
    from compensation_hub.db.models.compensation import Compensation


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    employee_code: Mapped[str] = mapped_column(String(20), unique=True)
    full_name: Mapped[str] = mapped_column(String(200))
    country: Mapped[str] = mapped_column(String(100))
    department: Mapped[str] = mapped_column(String(100))
    job_title: Mapped[str] = mapped_column(String(100))

    compensation: Mapped[Compensation | None] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )
