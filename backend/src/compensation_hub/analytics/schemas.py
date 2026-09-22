from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from compensation_hub.analytics.service import GroupBy


class SummaryRead(BaseModel):
    currency: Literal["USD"] = "USD"
    employee_count: int
    total_payroll_usd: Decimal
    average_salary_usd: Decimal | None


class BreakdownRowRead(BaseModel):
    key: str
    employee_count: int
    total_payroll_usd: Decimal
    average_salary_usd: Decimal | None


class BreakdownRead(BaseModel):
    group_by: GroupBy
    currency: Literal["USD"] = "USD"
    rows: list[BreakdownRowRead]
