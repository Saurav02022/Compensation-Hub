from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from compensation_hub.ask_compensation.provider import QueryPlanner
from compensation_hub.ask_compensation.schemas import AskRequest, AskResponse
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
    outcome = ask(session, payload.question, planner, payload.history)
    return AskResponse(
        status=outcome.status,
        question=payload.question,
        answer=outcome.answer,
        interpretation=outcome.interpretation,
        plan=outcome.plan,
        result=outcome.result,
        analytics_path=outcome.analytics_path,
    )
