from collections import Counter
from datetime import timedelta

from sqlmodel import Session, col, func, select

from app.core import limits
from app.core.config import settings
from app.db.models import CheckResult, Incident, Monitor, utcnow
from app.monitoring.scheduler import scheduler
from app.schemas.stats import AgentStatus, CheckHistory, CheckRead
from app.services import notifier


def monitor_history(
    session: Session, monitor_id: int, hours: int = 24, limit: int = 200
) -> CheckHistory:
    since = utcnow() - timedelta(hours=hours)
    where = [CheckResult.monitor_id == monitor_id, col(CheckResult.checked_at) >= since]

    total = session.exec(select(func.count()).select_from(CheckResult).where(*where)).one()
    ok_count = session.exec(
        select(func.count()).select_from(CheckResult).where(*where, col(CheckResult.ok).is_(True))
    ).one()
    average = session.exec(
        select(func.avg(CheckResult.response_time_ms)).where(
            *where, col(CheckResult.ok).is_(True)
        )
    ).one()
    rows = session.exec(
        select(CheckResult)
        .where(*where)
        .order_by(col(CheckResult.checked_at).desc())
        .limit(limit)
    ).all()

    return CheckHistory(
        monitor_id=monitor_id,
        hours=hours,
        total_checks=total,
        uptime_percent=round(ok_count / total * 100, 2) if total else None,
        avg_response_ms=int(average) if average is not None else None,
        checks=[CheckRead.model_validate(row) for row in rows],
    )


def overview(session: Session) -> AgentStatus:
    monitors = session.exec(select(Monitor)).all()
    by_status = Counter(m.status for m in monitors if m.enabled)
    open_incidents = session.exec(
        select(func.count()).select_from(Incident).where(col(Incident.resolved_at).is_(None))
    ).one()
    return AgentStatus(
        scheduler_running=scheduler.running,
        agent_enabled=settings.agent_enabled,
        email_configured=notifier.email_configured(),
        agent_runs_24h=limits.agent_runs_last_24h(session),
        agent_runs_limit=settings.max_agent_runs_per_day,
        monitors_total=len(monitors),
        monitors_up=by_status["up"],
        monitors_degraded=by_status["degraded"],
        monitors_down=by_status["down"],
        monitors_unknown=by_status["unknown"],
        monitors_paused=sum(1 for m in monitors if not m.enabled),
        open_incidents=open_incidents,
    )