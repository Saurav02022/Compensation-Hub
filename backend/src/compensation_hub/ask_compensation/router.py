from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from compensation_hub.ask_compensation.provider import QueryPlanner
from compensation_hub.ask_compensation.schemas import (
    AskRequest,
    AskResponse,
    AskResult,
    AskResultRow,
)
from compensation_hub.ask_compensation.service import ask
from compensation_hub.db.session import get_db_session

router = APIRouter(prefix="/analytics", tags=["ask-compensation"])


def get_query_planner(request: Request) -> QueryPlanner:
    planner: QueryPlanner = request.app.state.query_planner
    return planner


SessionDep = Annotated[Session, Depends(get_db_session)]
PlannerDep = Annotated[QueryPlanner, Depends(get_query_planner)]


@router.post("/ask", response_model=AskResponse)
def ask_compensation(session: SessionDep, planner: PlannerDep, payload: AskRequest) -> AskResponse:
    outcome = ask(session, payload.question, planner)
    result = None
    if outcome.status == "answered":
        result = AskResult(
            rows=[
                AskResultRow(
                    key=row.key or None,
                    employee_count=row.employee_count,
                    total_payroll_usd=row.total_payroll_usd,
                    average_salary_usd=row.average_salary_usd,
                )
                for row in outcome.rows
            ]
        )
    return AskResponse(
        status=outcome.status,
        question=payload.question,
        answer=outcome.answer,
        plan=outcome.plan,
        result=result,
    )
