from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class IncidentRead(BaseModel):
    id: int
    monitor_id: int
    monitor_name: str
    started_at: datetime
    resolved_at: Optional[datetime]
    duration_minutes: int
    status: str  # open | resolved
    severity: str
    summary: str
    probable_cause: str
    affected: list[str]
    suggestions: list[str]
    analyzed: bool  # True when the AI agent wrote the explanation
    alert_sent: bool