from datetime import timedelta

from sqlmodel import Session, col, func, select

from app.core.config import settings
from app.db.models import AgentRun, utcnow


def agent_runs_last_24h(session: Session) -> int:
    since = utcnow() - timedelta(hours=24)
    statement = (
        select(func.count()).select_from(AgentRun).where(col(AgentRun.created_at) >= since)
    )
    return session.exec(statement).one()


def agent_allowed(session: Session) -> bool:
    """True while we are under the daily cap on agent runs."""
    return agent_runs_last_24h(session) < settings.max_agent_runs_per_day
