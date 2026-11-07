from datetime import timedelta

import httpx
import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.config import settings
from app.db.models import AgentRun, CheckResult, Incident, Monitor, utcnow
from app.services import check_service, incident_service, notifier
from app.agent.schemas import IncidentReport, fallback_report
from app.core import limits

@pytest.fixture(autouse=True)
def fast_and_local(monkeypatch):
    monkeypatch.setattr(settings, "allow_private_targets", True)  # skip DNS lookups
    monkeypatch.setattr(settings, "recheck_delay_seconds", 0)  # no waiting in tests

@pytest.fixture(autouse=True)
def fake_email(monkeypatch):
    """Collect emails in a list instead of sending them."""
    sent = []
    monkeypatch.setattr(
        notifier,
        "send_email",
        lambda to, subject, body: sent.append((to, subject, body)) or True,
    )
    return sent

@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s

@pytest.fixture(autouse=True)
def fake_agent(monkeypatch):
    """The agent never calls the real LLM in tests. Calls are recorded here."""
    calls = []

    def fake(name, url, status, issues, **kwargs):
        calls.append((name, status))
        return IncidentReport(
            summary="AI summary",
            probable_cause="AI cause",
            severity="critical",
            suggestions=["Do this", "Do that"],
            confidence="high",
        )

    monkeypatch.setattr(check_service, "investigate", fake)
    monkeypatch.setattr(settings, "agent_enabled", True)
    monkeypatch.setattr(settings, "max_agent_runs_per_day", 20)
    return calls

def add_monitor(session, **overrides):
    data = dict(name="Test", url="http://site.test", alert_email="owner@example.com")
    data.update(overrides)
    monitor = Monitor(**data)
    session.add(monitor)
    session.commit()
    session.refresh(monitor)
    return monitor


def serve(statuses=None):
    """Fake website. statuses = {path: status}. Anything else answers 200."""
    statuses = statuses or {}

    def handler(request):
        code = statuses.get(request.url.path, 200)
        return httpx.Response(code, text="<html>ok</html>")

    return httpx.MockTransport(handler)


def test_healthy_site(session):
    monitor = add_monitor(session)
    summary = check_service.check_monitor(session, monitor.id, transport=serve())
    assert summary.status == "up"
    assert summary.transition == "none"
    session.refresh(monitor)
    assert monitor.status == "up"
    assert monitor.last_checked_at is not None
    assert len(session.exec(select(CheckResult)).all()) == 1
    assert session.exec(select(Incident)).all() == []


def test_site_down_opens_incident(session):
    monitor = add_monitor(session)
    summary = check_service.check_monitor(
        session, monitor.id, transport=serve({"/": 500})
    )
    assert summary.status == "down"
    assert summary.transition == "opened"
    incident = session.exec(select(Incident)).one()
    assert incident.severity == "critical"
    assert incident.resolved_at is None
    assert "500" in incident.affected[0]


def test_degraded_when_only_a_route_fails(session):
    monitor = add_monitor(session, routes=["/pricing"])
    summary = check_service.check_monitor(
        session, monitor.id, transport=serve({"/pricing": 404})
    )
    assert summary.status == "degraded"
    assert session.exec(select(Incident)).one().severity == "medium"


def test_same_problem_does_not_open_a_second_incident(session):
    monitor = add_monitor(session)
    broken = serve({"/": 500})
    check_service.check_monitor(session, monitor.id, transport=broken)
    summary = check_service.check_monitor(session, monitor.id, transport=broken)
    assert summary.transition == "updated"
    assert len(session.exec(select(Incident)).all()) == 1


def test_recovery_resolves_incident(session):
    monitor = add_monitor(session)
    check_service.check_monitor(session, monitor.id, transport=serve({"/": 500}))
    summary = check_service.check_monitor(session, monitor.id, transport=serve())
    assert summary.status == "up"
    assert summary.transition == "resolved"
    assert session.exec(select(Incident)).one().resolved_at is not None
    assert incident_service.get_open_incident(session, monitor.id) is None


def test_one_failed_request_is_not_an_incident(session):
    """First attempt fails, the confirmation attempt works: no alarm."""
    calls = {"home": 0}

    def flaky(request):
        if request.url.path == "/":
            calls["home"] += 1
            if calls["home"] == 1:
                return httpx.Response(500, text="boom")
        return httpx.Response(200, text="<html>ok</html>")

    monitor = add_monitor(session)
    summary = check_service.check_monitor(
        session, monitor.id, transport=httpx.MockTransport(flaky)
    )
    assert summary.status == "up"
    assert session.exec(select(Incident)).all() == []
    assert len(session.exec(select(CheckResult)).all()) == 1


def test_unknown_monitor_returns_none(session):
    assert check_service.check_monitor(session, 999) is None


def test_due_monitors(session):
    never = add_monitor(session, name="never")
    add_monitor(session, name="fresh", last_checked_at=utcnow())
    stale = add_monitor(
        session,
        name="stale",
        last_checked_at=utcnow() - timedelta(minutes=6),
        interval_minutes=5,
    )
    add_monitor(session, name="off", enabled=False)
    assert set(check_service.get_due_monitor_ids(session)) == {never.id, stale.id}


def test_old_results_are_pruned(session):
    monitor = add_monitor(session)
    old_time = utcnow() - timedelta(days=settings.check_retention_days + 1)
    session.add(CheckResult(monitor_id=monitor.id, ok=True, checked_at=old_time))
    session.add(CheckResult(monitor_id=monitor.id, ok=True))
    session.commit()
    check_service.prune_old_results(session)
    assert len(session.exec(select(CheckResult)).all()) == 1

def test_alert_email_sent_when_incident_opens(session, fake_email):
    monitor = add_monitor(session, name="Shop")
    check_service.check_monitor(session, monitor.id, transport=serve({"/": 500}))
    assert len(fake_email) == 1
    to, subject, body = fake_email[0]
    assert to == "owner@example.com"
    assert "[DOWN]" in subject
    assert "Shop" in subject
    assert session.exec(select(Incident)).one().alert_sent is True


def test_same_incident_sends_only_one_alert(session, fake_email):
    monitor = add_monitor(session)
    broken = serve({"/": 500})
    check_service.check_monitor(session, monitor.id, transport=broken)
    check_service.check_monitor(session, monitor.id, transport=broken)
    assert len(fake_email) == 1


def test_recovery_email_follows_the_alert(session, fake_email):
    monitor = add_monitor(session)
    check_service.check_monitor(session, monitor.id, transport=serve({"/": 500}))
    check_service.check_monitor(session, monitor.id, transport=serve())
    assert len(fake_email) == 2
    assert "[RECOVERED]" in fake_email[1][1]




def test_no_recovery_email_if_client_was_never_alerted(session, monkeypatch):
    attempts = []
    monkeypatch.setattr(
        notifier,
        "send_email",
        lambda to, subject, body: attempts.append(subject) or False,  # sending fails
    )
    monitor = add_monitor(session)
    check_service.check_monitor(session, monitor.id, transport=serve({"/": 500}))
    check_service.check_monitor(session, monitor.id, transport=serve())
    assert len(attempts) == 1  # only the alert attempt, no recovery email


def test_failed_alert_is_retried_on_the_next_check(session, monkeypatch):
    results = iter([False, True])
    attempts = []

    def flaky_send(to, subject, body):
        attempts.append(subject)
        return next(results)

    monkeypatch.setattr(notifier, "send_email", flaky_send)
    monitor = add_monitor(session)
    broken = serve({"/": 500})
    check_service.check_monitor(session, monitor.id, transport=broken)
    check_service.check_monitor(session, monitor.id, transport=broken)
    assert len(attempts) == 2
    assert session.exec(select(Incident)).one().alert_sent is True

def test_agent_explains_a_new_incident(session, fake_email, fake_agent):
    monitor = add_monitor(session)
    check_service.check_monitor(session, monitor.id, transport=serve({"/": 500}))
    incident = session.exec(select(Incident)).one()
    assert incident.summary == "AI summary"
    assert incident.probable_cause == "AI cause"
    assert incident.suggestions == ["Do this", "Do that"]
    assert incident.severity == "critical"  # decided by the code, not the LLM
    assert "AI cause" in fake_email[0][2]
    run = session.exec(select(AgentRun)).one()
    assert run.ai_generated is True
    assert len(fake_agent) == 1


def test_agent_runs_once_per_incident(session, fake_agent):
    monitor = add_monitor(session)
    broken = serve({"/": 500})
    check_service.check_monitor(session, monitor.id, transport=broken)
    check_service.check_monitor(session, monitor.id, transport=broken)
    assert len(fake_agent) == 1


def test_agent_does_not_run_for_a_healthy_site(session, fake_agent):
    monitor = add_monitor(session)
    check_service.check_monitor(session, monitor.id, transport=serve())
    assert fake_agent == []


def test_daily_cap_blocks_the_agent_but_not_the_alert(
    session, fake_email, fake_agent, monkeypatch
):
    monkeypatch.setattr(settings, "max_agent_runs_per_day", 0)
    monitor = add_monitor(session)
    check_service.check_monitor(session, monitor.id, transport=serve({"/": 500}))
    assert fake_agent == []
    assert len(fake_email) == 1
    assert session.exec(select(Incident)).one().probable_cause == ""


def test_agent_can_be_switched_off(session, fake_email, fake_agent, monkeypatch):
    monkeypatch.setattr(settings, "agent_enabled", False)
    monitor = add_monitor(session)
    check_service.check_monitor(session, monitor.id, transport=serve({"/": 500}))
    assert fake_agent == [] and len(fake_email) == 1


def test_agent_crash_does_not_block_the_alert(session, fake_email, monkeypatch):
    def crash(*args, **kwargs):
        raise RuntimeError("LLM down")

    monkeypatch.setattr(check_service, "investigate", crash)
    monitor = add_monitor(session)
    check_service.check_monitor(session, monitor.id, transport=serve({"/": 500}))
    assert len(fake_email) == 1
    assert session.exec(select(Incident)).one().probable_cause == ""


def test_plain_fallback_report_is_not_stored(session, fake_email, monkeypatch):
    monkeypatch.setattr(
        check_service, "investigate", lambda *a, **k: fallback_report("down", ["x"])
    )
    monitor = add_monitor(session)
    check_service.check_monitor(session, monitor.id, transport=serve({"/": 500}))
    assert session.exec(select(Incident)).one().probable_cause == ""
    assert len(fake_email) == 1


def test_low_confidence_cause_is_marked(session, monkeypatch):
    monkeypatch.setattr(
        check_service,
        "investigate",
        lambda *a, **k: IncidentReport(
            summary="s", probable_cause="maybe DNS", severity="high", confidence="low"
        ),
    )
    monitor = add_monitor(session)
    check_service.check_monitor(session, monitor.id, transport=serve({"/": 500}))
    cause = session.exec(select(Incident)).one().probable_cause
    assert cause.startswith("Possible cause (not certain)")


def test_agent_limit_counts_only_the_last_24_hours(session, monkeypatch):
    monkeypatch.setattr(settings, "max_agent_runs_per_day", 2)
    session.add(AgentRun(monitor_id=1, created_at=utcnow() - timedelta(hours=30)))
    session.add(AgentRun(monitor_id=1))
    session.commit()
    assert limits.agent_runs_last_24h(session) == 1
    assert limits.agent_allowed(session) is True
    session.add(AgentRun(monitor_id=1))
    session.commit()
    assert limits.agent_allowed(session) is False

def test_second_check_of_the_same_monitor_is_skipped(session):
    monitor = add_monitor(session)
    check_service._active.add(monitor.id)
    try:
        assert check_service.is_running(monitor.id) is True
        assert check_service.check_monitor(session, monitor.id, transport=serve()) is None
    finally:
        check_service._active.discard(monitor.id)
    assert session.exec(select(CheckResult)).all() == []
    assert check_service.is_running(monitor.id) is False

def test_plain_summary_follows_the_problems(session, monkeypatch):
    monkeypatch.setattr(settings, "agent_enabled", False)
    monitor = add_monitor(session, routes=["/pricing"])
    check_service.check_monitor(session, monitor.id, transport=serve({"/pricing": 404}))
    assert "/pricing" in session.exec(select(Incident)).one().summary
    check_service.check_monitor(
        session, monitor.id, transport=serve({"/": 500, "/pricing": 404})
    )
    assert "500" in session.exec(select(Incident)).one().summary

def test_new_problem_after_recovery_is_emailed(session, fake_email):
    monitor = add_monitor(session)
    broken = serve({"/": 500})
    check_service.check_monitor(session, monitor.id, transport=broken)
    check_service.check_monitor(session, monitor.id, transport=serve())
    check_service.check_monitor(session, monitor.id, transport=broken)
    assert len(fake_email) == 3  # DOWN, RECOVERED, DOWN
    assert "[DOWN]" in fake_email[2][1]


def test_flapping_site_is_muted_after_the_limit(session, fake_email, monkeypatch):
    monkeypatch.setattr(settings, "max_alerts_per_hour", 2)
    monitor = add_monitor(session)
    broken = serve({"/": 500})
    for _ in range(3):
        check_service.check_monitor(session, monitor.id, transport=broken)
        check_service.check_monitor(session, monitor.id, transport=serve())
    assert len([m for m in fake_email if "[DOWN]" in m[1]]) == 2


def test_each_new_incident_gets_its_own_agent_run(session, fake_agent):
    monitor = add_monitor(session)
    broken = serve({"/": 500})
    check_service.check_monitor(session, monitor.id, transport=broken)
    check_service.check_monitor(session, monitor.id, transport=serve())
    check_service.check_monitor(session, monitor.id, transport=broken)
    assert len(fake_agent) == 2