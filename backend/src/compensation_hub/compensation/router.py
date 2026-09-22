from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from compensation_hub.compensation.schemas import CompensationUpdate
from compensation_hub.compensation.service import update_compensation
from compensation_hub.db.session import get_db_session
from compensation_hub.employees.schemas import CompensationRead

router = APIRouter(prefix="/employees", tags=["compensation"])

SessionDep = Annotated[Session, Depends(get_db_session)]


@router.patch("/{employee_id}/compensation", response_model=CompensationRead)
def patch_compensation(
    session: SessionDep, employee_id: int, payload: CompensationUpdate
) -> CompensationRead:
    compensation = update_compensation(
        session, employee_id, payload.annual_salary, payload.currency_code
    )
    return CompensationRead.model_validate(compensation)
