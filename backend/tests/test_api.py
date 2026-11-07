from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.api.deps import require_admin
from app.api.routes import monitors as monitors_routes
from app.core.config import settings
from app.db.models import CheckResult, Incident, Monitor, utcnow
from app.db.session import get_session
from app.main import app
from app.monitoring import scheduler as scheduler_module
from app.services import check_service, notifier


@pytest.fixture()
def engine():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture()
def anon_client(engine):
    """A client that is NOT logged in (the real login lock is active)."""

    def override_session():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = override_session
    monitors_routes._last_test_email.clear()
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client(anon_client):
    """A logged-in client."""
    app.dependency_overrides[require_admin] = lambda: None
    return anon_client


def add(engine, obj):
    with Session(engine) as s:
        s.add(obj)
        s.commit()
        s.refresh(obj)
        return obj


def make_monitor(engine, **overrides):
    data = dict(name="Shop", url="https://shop.test", alert_email="owner@example.com")
    data.update(overrides)
    return add(engine, Monitor(**data))


#  login lock
@pytest.mark.parametrize(
    "path", ["/monitors", "/incidents", "/incidents/1", "/agent/status", "/monitors/1/checks"]
)
def test_routes_need_login(anon_client, path):
    assert anon_client.get(path).status_code == 401


def test_health_is_public(anon_client):
    assert anon_client.get("/health").status_code == 200


def test_real_login_flow(anon_client):
    wrong = anon_client.post("/auth/login", json={"password": "definitely-wrong"})
    assert wrong.status_code == 401
    ok = anon_client.post("/auth/login", json={"password": settings.admin_password})
    assert ok.status_code == 200
    token = ok.json()["access_token"]
    response = anon_client.get("/monitors", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


#  incidents
def test_incident_list_and_filters(client, engine):
    monitor = make_monitor(engine)
    add(engine, Incident(monitor_id=monitor.id, severity="critical", summary="old one",
                         resolved_at=utcnow()))
    add(engine, Incident(monitor_id=monitor.id, severity="critical", summary="new one",
                         probable_cause="DNS", suggestions=["Check DNS"]))

    everything = client.get("/incidents").json()
    assert [i["summary"] for i in everything] == ["new one", "old one"]  # newest first
    assert everything[0]["monitor_name"] == "Shop"
    assert everything[0]["status"] == "open"
    assert everything[0]["analyzed"] is True
    assert everything[1]["status"] == "resolved"
    assert everything[1]["analyzed"] is False

    assert len(client.get("/incidents?status=open").json()) == 1
    assert len(client.get("/incidents?status=resolved").json()) == 1
    assert len(client.get(f"/incidents?monitor_id={monitor.id}").json()) == 2
    assert client.get("/incidents?monitor_id=999").json() == []
    assert client.get("/incidents?status=nonsense").status_code == 422


def test_incident_detail_and_404(client, engine):
    monitor = make_monitor(engine)
    incident = add(engine, Incident(monitor_id=monitor.id, summary="boom"))
    assert client.get(f"/incidents/{incident.id}").json()["summary"] == "boom"
    assert client.get("/incidents/999").status_code == 404


def test_incident_duration(client, engine):
    monitor = make_monitor(engine)
    add(engine, Incident(monitor_id=monitor.id, started_at=utcnow() - timedelta(minutes=90),
                         resolved_at=utcnow()))
    assert client.get("/incidents").json()[0]["duration_minutes"] in (89, 90)


#  check history
def test_check_history_numbers(client, engine):
    monitor = make_monitor(engine)
    for ok, ms in [(True, 100), (True, 300), (True, 200), (False, None)]:
        add(engine, CheckResult(monitor_id=monitor.id, ok=ok, response_time_ms=ms))
    add(engine, CheckResult(monitor_id=monitor.id, ok=False,
                            checked_at=utcnow() - timedelta(hours=48)))  # outside 24h

    data = client.get(f"/monitors/{monitor.id}/checks").json()
    assert data["total_checks"] == 4
    assert data["uptime_percent"] == 75.0
    assert data["avg_response_ms"] == 200
    assert len(data["checks"]) == 4

    wide = client.get(f"/monitors/{monitor.id}/checks?hours=100").json()
    assert wide["total_checks"] == 5


def test_check_history_empty_and_404(client, engine):
    monitor = make_monitor(engine)
    data = client.get(f"/monitors/{monitor.id}/checks").json()
    assert data["total_checks"] == 0 and data["uptime_percent"] is None
    assert client.get("/monitors/999/checks").status_code == 404


#  agent status
def test_agent_status_counts(client, engine, monkeypatch):
    monkeypatch.setattr(notifier, "email_configured", lambda: True)
    make_monitor(engine, name="a", status="up")
    make_monitor(engine, name="b", status="down")
    make_monitor(engine, name="c", status="degraded")
    make_monitor(engine, name="d", status="up", enabled=False)
    down = make_monitor(engine, name="e", status="unknown")
    add(engine, Incident(monitor_id=down.id))

    data = client.get("/agent/status").json()
    assert data["monitors_total"] == 5
    assert data["monitors_up"] == 1
    assert data["monitors_down"] == 1
    assert data["monitors_degraded"] == 1
    assert data["monitors_unknown"] == 1
    assert data["monitors_paused"] == 1
    assert data["open_incidents"] == 1
    assert data["email_configured"] is True
    assert data["scheduler_running"] is False  # the test client does not start it
    assert data["agent_runs_limit"] == settings.max_agent_runs_per_day


#  check now
def test_check_now_starts_a_check(client, engine, monkeypatch):
    monitor = make_monitor(engine)
    started = []
    monkeypatch.setattr(scheduler_module, "check_now", started.append)
    response = client.post(f"/monitors/{monitor.id}/check-now")
    assert response.status_code == 202
    assert started == [monitor.id]


def test_check_now_refused_while_a_check_runs(client, engine, monkeypatch):
    monitor = make_monitor(engine)
    monkeypatch.setattr(check_service, "is_running", lambda monitor_id: True)
    assert client.post(f"/monitors/{monitor.id}/check-now").status_code == 409


def test_check_now_unknown_monitor(client):
    assert client.post("/monitors/999/check-now").status_code == 404


# test email
def test_test_email_is_sent_then_rate_limited(client, engine, monkeypatch):
    monitor = make_monitor(engine)
    sent = []
    monkeypatch.setattr(notifier, "email_configured", lambda: True)
    monkeypatch.setattr(
        notifier, "send_email", lambda to, subject, body: sent.append(to) or True
    )
    first = client.post(f"/monitors/{monitor.id}/test-email")
    assert first.status_code == 200
    assert first.json() == {"sent": True, "to": "owner@example.com"}
    assert client.post(f"/monitors/{monitor.id}/test-email").status_code == 429
    assert sent == ["owner@example.com"]


def test_test_email_when_email_is_not_configured(client, engine, monkeypatch):
    monitor = make_monitor(engine)
    monkeypatch.setattr(notifier, "email_configured", lambda: False)
    assert client.post(f"/monitors/{monitor.id}/test-email").status_code == 503

def test_failed_test_email_gives_an_error_and_no_wait(client, engine, monkeypatch):
    monitor = make_monitor(engine)
    monkeypatch.setattr(notifier, "email_configured", lambda: True)
    monkeypatch.setattr(notifier, "send_email", lambda to, subject, body: False)
    assert client.post(f"/monitors/{monitor.id}/test-email").status_code == 502
    assert client.post(f"/monitors/{monitor.id}/test-email").status_code == 502

def test_cors_allows_the_dashboard_origin(anon_client):
    origin = settings.cors_origin_list[0]
    response = anon_client.options(
        "/auth/login",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


def test_cors_refuses_other_origins(anon_client):
    response = anon_client.options(
        "/auth/login",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers