from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CompensationUpdate(BaseModel):
    """Replacement values for an employee's current compensation."""

    model_config = ConfigDict(extra="forbid")

    annual_salary: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    currency_code: str = Field(pattern=r"^[A-Z]{3}$")
