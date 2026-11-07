import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
import threading

import httpx
from sqlmodel import Session, col, delete, func, select

from app.core.config import settings
from app.db.models import AgentRun, CheckResult, Incident, Monitor, utcnow
from app.monitoring.checks import RunReport, run_checks
from app.services import incident_service, notifier
from app.agent.agent import investigate
from app.core import limits


logger = logging.getLogger(__name__)
_active_lock = threading.Lock()
_active: set[int] = set()

# A monitor counts as due a few seconds early, so the 60-second tick
# never makes a 5-minute check drift to 6 minutes.
DUE_SLACK_SECONDS = 10


@dataclass
class CheckSummary:
    monitor_id: int
    status: str  # up | degraded | down
    issues: list[str]
    transition: str  # none | opened | updated | resolved
    incident_id: Optional[int] = None


def _as_utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def status_from(report: RunReport) -> str:
    if report.ok:
        return "up"
    if report.status_code is None or report.status_code >= 400:
        return "down"  # the main page itself failed
    return "degraded"  # main page works, something else is broken


def get_due_monitor_ids(session: Session) -> list[int]:
    now = utcnow()
    due = []
    monitors = session.exec(select(Monitor).where(col(Monitor.enabled).is_(True))).all()
    for monitor in monitors:
        last = _as_utc(monitor.last_checked_at)
        if last is None:
            due.append(monitor.id)
            continue
        next_run = last + timedelta(minutes=monitor.interval_minutes)
        if now >= next_run - timedelta(seconds=DUE_SLACK_SECONDS):
            due.append(monitor.id)
    return due


def _run(monitor: Monitor, transport: Optional[httpx.BaseTransport]) -> RunReport:
    return run_checks(
        monitor.url,
        routes=monitor.routes,
        api_endpoints=monitor.api_endpoints,
        transport=transport,
    )


def _update_incident(
    session: Session, monitor_id: int, status: str, report: RunReport
) -> tuple[str, Optional[int]]:
    open_one = incident_service.get_open_incident(session, monitor_id)

    if report.ok:
        if open_one:
            incident_service.resolve_incident(session, open_one)
            return "resolved", open_one.id
        return "none", None

    if open_one:
        incident_service.update_incident(session, open_one, status, report.issues)
        return "updated", open_one.id

    created = incident_service.open_incident(session, monitor_id, status, report.issues)
    return "opened", created.id

def _alert_limit_reached(session: Session, monitor: Monitor) -> bool:
    since = utcnow() - timedelta(hours=1)
    sent = session.exec(
        select(func.count())
        .select_from(Incident)
        .where(
            Incident.monitor_id == monitor.id,
            col(Incident.alert_sent).is_(True),
            col(Incident.started_at) >= since,
        )
    ).one()
    return sent >= settings.max_alerts_per_hour


def _analyze(session: Session, monitor: Monitor, incident: Incident) -> None:
    """Ask the agent to explain a new incident. Never raises."""
    if not settings.agent_enabled:
        return
    if not limits.agent_allowed(session):
        logger.warning(
            "Daily agent limit reached: incident %s gets the plain alert", incident.id
        )
        return

    # Count the attempt BEFORE calling the LLM, so a crash can never skip the cap
    run = AgentRun(monitor_id=monitor.id, incident_id=incident.id)
    session.add(run)
    session.commit()

    try:
        report = investigate(
            monitor.name, monitor.url, monitor.status, list(incident.affected or [])
        )
    except Exception:
        logger.exception("Agent crashed for incident %s", incident.id)
        return
    if not report.ai_generated:
        return  # the plain fallback report adds nothing, so keep the plain alert

    cause = report.probable_cause
    if report.confidence == "low":
        cause = f"Possible cause (not certain): {cause}"

    run.ai_generated = True
    incident.summary = report.summary
    incident.probable_cause = cause
    incident.suggestions = list(report.suggestions)
    session.add(run)
    session.add(incident)
    session.commit()


def _try_alert(session: Session, monitor: Monitor, incident: Incident) -> None:
    if _alert_limit_reached(session, monitor):
        logger.info("Alert for monitor %s held back: too many alerts this hour", monitor.id)
        return
    if notifier.send_incident_alert(monitor, incident):
        incident.alert_sent = True
        monitor.last_alert_at = utcnow()
        session.add(incident)
        session.add(monitor)
        session.commit()


def _notify(
    session: Session, monitor: Monitor, transition: str, incident_id: Optional[int]
) -> None:
    """Explain (for new incidents) and email the client. Never stops monitoring."""
    if incident_id is None:
        return
    try:
        incident = session.get(Incident, incident_id)
        if incident is None:
            return
        if transition == "resolved":
            if incident.alert_sent:  # only tell them it is fixed if they heard of it
                notifier.send_recovery_notice(monitor, incident)
        elif transition in ("opened", "updated") and not incident.alert_sent:
            if transition == "opened" and not _alert_limit_reached(session, monitor):
                _analyze(session, monitor, incident)
            _try_alert(session, monitor, incident)
    except Exception:
        logger.exception("Notification failed for monitor %s", monitor.id)
        
def _check_monitor(
    session: Session,
    monitor_id: int,
    transport: Optional[httpx.BaseTransport] = None,
) -> Optional[CheckSummary]:
    """Check one monitor, save the result, open/update/resolve its incident."""
    monitor = session.get(Monitor, monitor_id)
    if monitor is None:
        return None

    started = utcnow()
    report = _run(monitor, transport)
    if not report.ok:
        # Confirm before believing it: one failed check can be a network blip
        time.sleep(settings.recheck_delay_seconds)
        report = _run(monitor, transport)

    status = status_from(report)
    session.add(
        CheckResult(
            monitor_id=monitor.id,
            ok=report.ok,
            status_code=report.status_code,
            response_time_ms=report.response_time_ms,
            issues=report.issues,
        )
    )
    monitor.status = status
    monitor.last_checked_at = started
    session.add(monitor)
    session.commit()

    transition, incident_id = _update_incident(session, monitor.id, status, report)
    _notify(session, monitor, transition, incident_id)
    logger.info(
        "Checked monitor %s (%s): %s, %d issue(s), incident: %s",
        monitor.id,
        monitor.url,
        status,
        len(report.issues),
        transition,
    )
    return CheckSummary(
        monitor_id=monitor.id,
        status=status,
        issues=report.issues,
        transition=transition,
        incident_id=incident_id,
    )

def is_running(monitor_id: int) -> bool:
    with _active_lock:
        return monitor_id in _active


def check_monitor(
    session: Session,
    monitor_id: int,
    transport: Optional[httpx.BaseTransport] = None,
) -> Optional[CheckSummary]:
    """Check one monitor. If it is already being checked right now, skip it."""
    with _active_lock:
        if monitor_id in _active:
            logger.info("Monitor %s is already being checked: skipped", monitor_id)
            return None
        _active.add(monitor_id)
    try:
        return _check_monitor(session, monitor_id, transport)
    finally:
        with _active_lock:
            _active.discard(monitor_id)



def prune_old_results(session: Session) -> None:
    """Delete check history older than the retention period."""
    cutoff = utcnow() - timedelta(days=settings.check_retention_days)
    session.exec(delete(CheckResult).where(col(CheckResult.checked_at) < cutoff))
    session.exec(delete(AgentRun).where(col(AgentRun.created_at) < cutoff))
    session.commit()