from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    """Current time in UTC (timezone-aware)."""
    return datetime.now(timezone.utc)

def as_utc(value: Optional[datetime]) -> Optional[datetime]:
    """Make a datetime timezone-aware (SQLite may give back a naive one)."""
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value

class Monitor(SQLModel, table=True):
    """A website we watch, plus all its settings (editable from the dashboard)."""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    url: str
    routes: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    api_endpoints: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    alert_email: str
    interval_minutes: int = 5
    enabled: bool = True

    # Current state, used to alert only on changes (up -> down, down -> up)
    status: str = "unknown"  # unknown | up | down
    last_checked_at: Optional[datetime] = None
    last_alert_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utcnow)


class CheckResult(SQLModel, table=True):
    """One run of the quick health checks for a monitor."""

    id: Optional[int] = Field(default=None, primary_key=True)
    monitor_id: int = Field(foreign_key="monitor.id", index=True)
    checked_at: datetime = Field(default_factory=utcnow)
    ok: bool
    status_code: Optional[int] = None
    response_time_ms: Optional[int] = None
    issues: list[str] = Field(default_factory=list, sa_column=Column(JSON))


class Incident(SQLModel, table=True):
    """A problem found by the agent, with its explanation and advice."""

    id: Optional[int] = Field(default=None, primary_key=True)
    monitor_id: int = Field(foreign_key="monitor.id", index=True)
    started_at: datetime = Field(default_factory=utcnow)
    resolved_at: Optional[datetime] = None

    severity: str = "medium"  # low | medium | high | critical
    summary: str = ""
    probable_cause: str = ""
    affected: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    suggestions: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    alert_sent: bool = False

class AgentRun(SQLModel, table=True):
    """One agent investigation attempt. Used to enforce the daily cap."""

    id: Optional[int] = Field(default=None, primary_key=True)
    monitor_id: int = Field(index=True)
    incident_id: Optional[int] = None
    created_at: datetime = Field(default_factory=utcnow, index=True)
    ai_generated: bool = False