import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from sqlmodel import Session

from app.core.config import settings
from app.db.session import engine
from app.services import check_service

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="UTC")


def _check_one(monitor_id: int) -> None:
    # One broken check must never stop the others (or the scheduler)
    try:
        with Session(engine) as session:
            check_service.check_monitor(session, monitor_id)
    except Exception:
        logger.exception("Check crashed for monitor %s", monitor_id)


def tick() -> None:
    """Runs every minute: find monitors that are due and check them."""
    with Session(engine) as session:
        due_ids = check_service.get_due_monitor_ids(session)
    if not due_ids:
        return
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(_check_one, due_ids))


def prune() -> None:
    try:
        with Session(engine) as session:
            check_service.prune_old_results(session)
    except Exception:
        logger.exception("Pruning old results failed")


def start_scheduler() -> None:
    if not settings.scheduler_enabled:
        logger.info("Scheduler is disabled by settings")
        return
    if scheduler.running:
        return
    scheduler.add_job(
        tick,
        "interval",
        seconds=60,
        id="tick",
        replace_existing=True,
        max_instances=1,  # a slow tick never overlaps the next one
        coalesce=True,
        misfire_grace_time=30,
        next_run_time=datetime.now(timezone.utc),  # first run right at startup
    )
    scheduler.add_job(prune, "cron", hour=3, minute=0, id="prune", replace_existing=True)
    scheduler.start()
    logger.info("Scheduler started")


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)

def check_now(monitor_id: int) -> None:
    """Run one check immediately (used by the 'Check now' button)."""
    _check_one(monitor_id)

