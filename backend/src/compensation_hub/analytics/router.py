from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from compensation_hub.analytics.schemas import BreakdownRead, BreakdownRowRead, SummaryRead
from compensation_hub.analytics.service import (
    MAX_BREAKDOWN_LIMIT,
    AnalyticsFilters,
    GroupBy,
    SortBy,
    get_breakdown,
    get_summary,
)
from compensation_hub.db.session import get_db_session

router = APIRouter(prefix="/analytics", tags=["analytics"])

SessionDep = Annotated[Session, Depends(get_db_session)]
FilterValue = Annotated[str | None, Query(min_length=1, max_length=100)]


def analytics_filters(
    country: FilterValue = None,
    department: FilterValue = None,
    job_title: FilterValue = None,
) -> AnalyticsFilters:
    return AnalyticsFilters(country=country, department=department, job_title=job_title)


FiltersDep = Annotated[AnalyticsFilters, Depends(analytics_filters)]


@router.get("/summary", response_model=SummaryRead)
def read_summary(session: SessionDep, filters: FiltersDep) -> SummaryRead:
    summary = get_summary(session, filters)
    return SummaryRead(
        employee_count=summary.employee_count,
        total_payroll_usd=summary.total_payroll_usd,
        average_salary_usd=summary.average_salary_usd,
    )


@router.get("/breakdown", response_model=BreakdownRead)
def read_breakdown(
    session: SessionDep,
    filters: FiltersDep,
    group_by: GroupBy,
    sort_by: SortBy = "key",
    descending: bool = False,
    limit: Annotated[int | None, Query(ge=1, le=MAX_BREAKDOWN_LIMIT)] = None,
) -> BreakdownRead:
    rows = get_breakdown(
        session, group_by, filters, sort_by=sort_by, descending=descending, limit=limit
    )
    return BreakdownRead(
        group_by=group_by,
        rows=[
            BreakdownRowRead(
                key=row.key,
                employee_count=row.employee_count,
                total_payroll_usd=row.total_payroll_usd,
                average_salary_usd=row.average_salary_usd,
            )
            for row in rows
        ],
    )
