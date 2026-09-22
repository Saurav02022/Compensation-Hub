from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class CompensationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    annual_salary: Decimal
    currency_code: str


class EmployeeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_code: str
    full_name: str
    country: str
    department: str
    job_title: str
    compensation: CompensationRead | None


class EmployeePage(BaseModel):
    items: list[EmployeeRead]
    page: int
    page_size: int
    total_items: int
    total_pages: int


class EmployeeFilterOptions(BaseModel):
    countries: list[str]
    departments: list[str]
    job_titles: list[str]
