from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from compensation_hub.ask_compensation.provider import PlannerTurn, QueryPlanner
from compensation_hub.ask_compensation.schemas import (
    AnalyticsViewRead,
    AskRequest,
    AskResponse,
    AskResultRead,
    ResultColumnRead,
    ResultRowRead,
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
    history = [
        PlannerTurn(question=turn.question, sql=turn.sql, currency=turn.currency)
        for turn in payload.history
    ]
    outcome = ask(session, payload.question, history, planner)

    result = None
    if outcome.result is not None:
        result = AskResultRead(
            kind="scalar" if outcome.scalar else "table",
            columns=[
                ResultColumnRead(
                    key=column.key,
                    label=column.label,
                    type=column.type,
                    currency=column.currency,
                    currency_key=column.currency_key,
                )
                for column in outcome.result.columns
            ],
            rows=[
                ResultRowRead(values=list(row.values), employee_id=row.employee_id)
                for row in outcome.result.rows
            ],
            primary=outcome.primary,
            total_rows=outcome.result.total_rows,
        )

    return AskResponse(
        status=outcome.status,
        question=payload.question,
        answer=outcome.answer,
        interpretation=outcome.interpretation,
        missing=list(outcome.missing),
        sql=outcome.sql,
        currency=outcome.currency,
        result=result,
        analytics_view=(
            AnalyticsViewRead.model_validate(outcome.analytics_view)
            if outcome.analytics_view is not None
            else None
        ),
    )
