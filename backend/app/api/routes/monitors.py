import time

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.db.models import Monitor
from app.db.session import get_session
from app.monitoring import scheduler as scheduler_module
from app.monitoring.url_guard import UnsafeURLError, validate_url
from app.schemas.monitor import MonitorCreate, MonitorRead, MonitorUpdate
from app.schemas.stats import CheckHistory
from app.services import check_service, monitor_service, notifier, stats_service

router = APIRouter(prefix="/monitors", tags=["monitors"])

TEST_EMAIL_COOLDOWN_SECONDS = 60
_last_test_email: dict[int, float] = {}


def _get_or_404(session: Session, monitor_id: int) -> Monitor:
    monitor = monitor_service.get_monitor(session, monitor_id)
    if monitor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Monitor not found")
    return monitor


def _validate_targets(url, routes, api_endpoints) -> None:
    """Check the main URL and any full URLs listed in routes/endpoints."""
    targets = [url] if url else []
    for item in (routes or []) + (api_endpoints or []):
        if item.startswith(("http://", "https://")):
            targets.append(item)
    try:
        for target in targets:
            validate_url(target)
    except UnsafeURLError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))


@router.get("", response_model=list[MonitorRead])
def list_monitors(session: Session = Depends(get_session)):
    return monitor_service.list_monitors(session)


@router.post("", response_model=MonitorRead, status_code=status.HTTP_201_CREATED)
def create_monitor(data: MonitorCreate, session: Session = Depends(get_session)):
    _validate_targets(data.url, data.routes, data.api_endpoints)
    return monitor_service.create_monitor(session, data)


@router.get("/{monitor_id}", response_model=MonitorRead)
def get_monitor(monitor_id: int, session: Session = Depends(get_session)):
    return _get_or_404(session, monitor_id)


@router.patch("/{monitor_id}", response_model=MonitorRead)
def update_monitor(
    monitor_id: int, data: MonitorUpdate, session: Session = Depends(get_session)
):
    monitor = _get_or_404(session, monitor_id)
    _validate_targets(data.url, data.routes, data.api_endpoints)
    return monitor_service.update_monitor(session, monitor, data)


@router.delete("/{monitor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_monitor(monitor_id: int, session: Session = Depends(get_session)):
    monitor = _get_or_404(session, monitor_id)
    monitor_service.delete_monitor(session, monitor)


@router.get("/{monitor_id}/checks", response_model=CheckHistory)
def get_check_history(
    monitor_id: int,
    hours: int = Query(24, ge=1, le=720),
    limit: int = Query(200, ge=1, le=1000),
    session: Session = Depends(get_session),
):
    _get_or_404(session, monitor_id)
    return stats_service.monitor_history(session, monitor_id, hours, limit)


@router.post("/{monitor_id}/check-now", status_code=status.HTTP_202_ACCEPTED)
def check_now(
    monitor_id: int,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    _get_or_404(session, monitor_id)
    if check_service.is_running(monitor_id):
        raise HTTPException(status.HTTP_409_CONFLICT, "A check is already running")
    background_tasks.add_task(scheduler_module.check_now, monitor_id)
    return {"message": "Check started. Refresh in a few seconds to see the result."}


@router.post("/{monitor_id}/test-email")
def send_test_email(monitor_id: int, session: Session = Depends(get_session)):
    monitor = _get_or_404(session, monitor_id)
    if not notifier.email_configured():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Email is not set up on the server (SMTP settings are missing)",
        )
    last = _last_test_email.get(monitor_id)
    if last is not None and time.monotonic() - last < TEST_EMAIL_COOLDOWN_SECONDS:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Please wait a minute before sending another test email",
        )
    _last_test_email[monitor_id] = time.monotonic()
    sent = notifier.send_email(
        monitor.alert_email,
        f"Test alert from Website Monitor ({monitor.name})",
        "This is a test message.\n\nIf you can read it, alerts for "
        f"{monitor.url} will reach this address.\n\n"
        "-- Website Monitor Agent (automatic message)",
    )
    if not sent:
        _last_test_email.pop(monitor_id, None)  # a failed send must not start the wait
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "The email could not be sent. Check the server's internet connection and SMTP settings.",
        )
    return {"sent": True, "to": monitor.alert_email}