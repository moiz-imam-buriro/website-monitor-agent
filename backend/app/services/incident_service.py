from typing import Optional
from sqlmodel import Session, col, select
from app.db.models import Incident, Monitor, utcnow, as_utc
from app.schemas.incident import IncidentRead

def get_open_incident(session: Session, monitor_id: int) -> Optional[Incident]:
    statement = (
        select(Incident)
        .where(Incident.monitor_id == monitor_id, col(Incident.resolved_at).is_(None))
        .order_by(col(Incident.id).desc())
    )
    return session.exec(statement).first()


def _summary(issues: list[str]) -> str:
    if not issues:
        return "No problems"
    if len(issues) == 1:
        return issues[0]
    return f"{issues[0]} (and {len(issues) - 1} more problem(s))"


def _severity(status: str) -> str:
    return "critical" if status == "down" else "medium"


def open_incident(
    session: Session, monitor_id: int, status: str, issues: list[str]
) -> Incident:
    incident = Incident(
        monitor_id=monitor_id,
        severity=_severity(status),
        summary=_summary(issues),
        affected=list(issues),
    )
    session.add(incident)
    session.commit()
    session.refresh(incident)
    return incident


def update_incident(
    session: Session, incident: Incident, status: str, issues: list[str]
) -> Incident:
    incident.severity = _severity(status)
    incident.affected = list(issues)
    if not incident.probable_cause:  # no AI explanation: keep the plain summary current
        incident.summary = _summary(issues)
    session.add(incident)
    session.commit()
    session.refresh(incident)
    return incident


def resolve_incident(session: Session, incident: Incident) -> Incident:
    incident.resolved_at = utcnow()
    session.add(incident)
    session.commit()
    session.refresh(incident)
    return incident

def to_read(incident: Incident, monitor_name: str) -> IncidentRead:
    started = as_utc(incident.started_at)
    ended = as_utc(incident.resolved_at) or utcnow()
    minutes = max(0, int((ended - started).total_seconds() // 60))
    return IncidentRead(
        id=incident.id,
        monitor_id=incident.monitor_id,
        monitor_name=monitor_name,
        started_at=incident.started_at,
        resolved_at=incident.resolved_at,
        duration_minutes=minutes,
        status="resolved" if incident.resolved_at else "open",
        severity=incident.severity,
        summary=incident.summary,
        probable_cause=incident.probable_cause,
        affected=list(incident.affected or []),
        suggestions=list(incident.suggestions or []),
        analyzed=bool(incident.probable_cause),
        alert_sent=incident.alert_sent,
    )


def list_incidents(
    session: Session,
    monitor_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[IncidentRead]:
    statement = select(Incident, Monitor.name).join(
        Monitor, col(Monitor.id) == col(Incident.monitor_id)
    )
    if monitor_id is not None:
        statement = statement.where(Incident.monitor_id == monitor_id)
    if status == "open":
        statement = statement.where(col(Incident.resolved_at).is_(None))
    elif status == "resolved":
        statement = statement.where(col(Incident.resolved_at).is_not(None))
    statement = statement.order_by(col(Incident.id).desc()).offset(offset).limit(limit)
    return [to_read(i, name) for i, name in session.exec(statement).all()]


def get_incident_read(session: Session, incident_id: int) -> Optional[IncidentRead]:
    statement = (
        select(Incident, Monitor.name)
        .join(Monitor, col(Monitor.id) == col(Incident.monitor_id))
        .where(Incident.id == incident_id)
    )
    row = session.exec(statement).first()
    return to_read(row[0], row[1]) if row else None