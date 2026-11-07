from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db.session import get_session
from app.schemas.stats import AgentStatus
from app.services import stats_service

router = APIRouter(prefix="/agent", tags=["agent"])


@router.get("/status", response_model=AgentStatus)
def agent_status(session: Session = Depends(get_session)):
    return stats_service.overview(session)