from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from compensation_hub.db.session import get_db_session
from compensation_hub.employees.schemas import EmployeeFilterOptions, EmployeePage, EmployeeRead
from compensation_hub.employees.service import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    EmployeeQuery,
    get_employee,
    list_employees,
    list_filter_options,
)

router = APIRouter(prefix="/employees", tags=["employees"])

SessionDep = Annotated[Session, Depends(get_db_session)]
FilterValue = Annotated[str | None, Query(min_length=1, max_length=100)]


@router.get("", response_model=EmployeePage)
def read_employees(
    session: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
    search: FilterValue = None,
    country: FilterValue = None,
    department: FilterValue = None,
    job_title: FilterValue = None,
) -> EmployeePage:
    result = list_employees(
        session,
        EmployeeQuery(
            search=search,
            country=country,
            department=department,
            job_title=job_title,
            page=page,
            page_size=page_size,
        ),
    )
    return EmployeePage(
        items=[EmployeeRead.model_validate(employee) for employee in result.items],
        page=result.page,
        page_size=result.page_size,
        total_items=result.total_items,
        total_pages=result.total_pages,
    )


@router.get("/filter-options", response_model=EmployeeFilterOptions)
def read_filter_options(session: SessionDep) -> EmployeeFilterOptions:
    options = list_filter_options(session)
    return EmployeeFilterOptions(
        countries=list(options.countries),
        departments=list(options.departments),
        job_titles=list(options.job_titles),
    )


@router.get("/{employee_id}", response_model=EmployeeRead)
def read_employee(session: SessionDep, employee_id: int) -> EmployeeRead:
    return EmployeeRead.model_validate(get_employee(session, employee_id))
