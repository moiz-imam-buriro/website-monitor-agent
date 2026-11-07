from typing import Optional, Sequence

from sqlmodel import Session, delete, select

from app.db.models import AgentRun, CheckResult, Incident, Monitor
from app.schemas.monitor import MonitorCreate, MonitorUpdate


def list_monitors(session: Session) -> Sequence[Monitor]:
    return session.exec(select(Monitor).order_by(Monitor.id)).all()


def get_monitor(session: Session, monitor_id: int) -> Optional[Monitor]:
    return session.get(Monitor, monitor_id)


def create_monitor(session: Session, data: MonitorCreate) -> Monitor:
    monitor = Monitor(**data.model_dump())
    session.add(monitor)
    session.commit()
    session.refresh(monitor)
    return monitor


def update_monitor(session: Session, monitor: Monitor, data: MonitorUpdate) -> Monitor:
    changes = data.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(monitor, key, value)

    # A new URL means the old up/down state is no longer valid
    if "url" in changes:
        monitor.status = "unknown"
        monitor.last_checked_at = None

    session.add(monitor)
    session.commit()
    session.refresh(monitor)
    return monitor


def delete_monitor(session: Session, monitor: Monitor) -> None:
    # Remove the monitor's history first so no orphan rows are left
    session.exec(delete(CheckResult).where(CheckResult.monitor_id == monitor.id))
    session.exec(delete(Incident).where(Incident.monitor_id == monitor.id))
    session.exec(delete(AgentRun).where(AgentRun.monitor_id == monitor.id))
    session.delete(monitor)
    session.commit()