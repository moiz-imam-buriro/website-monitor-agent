from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CheckRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    checked_at: datetime
    ok: bool
    status_code: Optional[int]
    response_time_ms: Optional[int]
    issues: list[str]


class CheckHistory(BaseModel):
    monitor_id: int
    hours: int
    total_checks: int
    uptime_percent: Optional[float]  # None when there are no checks yet
    avg_response_ms: Optional[int]
    checks: list[CheckRead]  # newest first


class AgentStatus(BaseModel):
    scheduler_running: bool
    agent_enabled: bool
    email_configured: bool
    agent_runs_24h: int
    agent_runs_limit: int
    monitors_total: int
    monitors_up: int
    monitors_degraded: int
    monitors_down: int
    monitors_unknown: int
    monitors_paused: int
    open_incidents: int