from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.db.session import get_session
from app.schemas.incident import IncidentRead
from app.services import incident_service

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("", response_model=list[IncidentRead])
def list_incidents(
    monitor_id: Optional[int] = None,
    status_filter: Optional[Literal["open", "resolved"]] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
):
    return incident_service.list_incidents(session, monitor_id, status_filter, limit, offset)


@router.get("/{incident_id}", response_model=IncidentRead)
def get_incident(incident_id: int, session: Session = Depends(get_session)):
    incident = incident_service.get_incident_read(session, incident_id)
    if incident is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Incident not found")
    return incident