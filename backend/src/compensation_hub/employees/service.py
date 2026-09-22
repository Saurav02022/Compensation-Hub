import math
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import InstrumentedAttribute, Session, joinedload

from compensation_hub.db.models import Employee

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 25


class EmployeeNotFoundError(Exception):
    def __init__(self, employee_id: int) -> None:
        super().__init__(f"Employee {employee_id} not found")
        self.employee_id = employee_id


@dataclass(frozen=True)
class EmployeeQuery:
    search: str | None = None
    country: str | None = None
    department: str | None = None
    job_title: str | None = None
    page: int = 1
    page_size: int = DEFAULT_PAGE_SIZE


@dataclass(frozen=True)
class EmployeePageResult:
    items: Sequence[Employee]
    page: int
    page_size: int
    total_items: int

    @property
    def total_pages(self) -> int:
        return max(1, math.ceil(self.total_items / self.page_size))


@dataclass(frozen=True)
class FilterOptions:
    countries: Sequence[str]
    departments: Sequence[str]
    job_titles: Sequence[str]


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _apply_filters(
    statement: Select[tuple[Employee]], query: EmployeeQuery
) -> Select[tuple[Employee]]:
    if query.search:
        pattern = f"%{_escape_like(query.search.strip())}%"
        statement = statement.where(
            or_(
                Employee.full_name.ilike(pattern, escape="\\"),
                Employee.employee_code.ilike(pattern, escape="\\"),
            )
        )
    if query.country:
        statement = statement.where(Employee.country == query.country)
    if query.department:
        statement = statement.where(Employee.department == query.department)
    if query.job_title:
        statement = statement.where(Employee.job_title == query.job_title)
    return statement


def list_employees(session: Session, query: EmployeeQuery) -> EmployeePageResult:
    """Return one page of employees matching the query, with filtering and paging in PostgreSQL."""
    filtered = _apply_filters(select(Employee), query)

    total_items = session.scalar(select(func.count()).select_from(filtered.subquery())) or 0

    items = session.scalars(
        filtered.options(joinedload(Employee.compensation))
        .order_by(Employee.full_name, Employee.employee_code)
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    ).all()

    return EmployeePageResult(
        items=items, page=query.page, page_size=query.page_size, total_items=total_items
    )


def get_employee(session: Session, employee_id: int) -> Employee:
    employee = session.get(Employee, employee_id, options=[joinedload(Employee.compensation)])
    if employee is None:
        raise EmployeeNotFoundError(employee_id)
    return employee


def list_filter_options(session: Session) -> FilterOptions:
    def distinct_values(column: InstrumentedAttribute[str]) -> Sequence[str]:
        return session.scalars(select(column).distinct().order_by(column)).all()

    return FilterOptions(
        countries=distinct_values(Employee.country),
        departments=distinct_values(Employee.department),
        job_titles=distinct_values(Employee.job_title),
    )
