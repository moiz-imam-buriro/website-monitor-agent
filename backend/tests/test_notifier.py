import smtplib
import pytest

from app.core.config import Settings, settings
from app.db.models import Incident, Monitor, utcnow
from app.services import notifier


class FakeSMTP:
    sent = []
    fail_login = False

    def __init__(self, host, port, timeout=None):
        self.host, self.port = host, port

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def starttls(self):
        pass

    def login(self, user, password):
        if FakeSMTP.fail_login:
            raise smtplib.SMTPAuthenticationError(535, b"bad credentials")

    def send_message(self, message):
        FakeSMTP.sent.append(message)


@pytest.fixture(autouse=True)
def fake_smtp(monkeypatch):
    FakeSMTP.sent = []
    FakeSMTP.fail_login = False
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(smtplib, "SMTP_SSL", FakeSMTP)
    monkeypatch.setattr(settings, "smtp_user", "monitor@example.com")
    monkeypatch.setattr(settings, "smtp_password", "secret")
    monkeypatch.setattr(settings, "smtp_from", "monitor@example.com")
    monkeypatch.setattr(settings, "brevo_api_key", "")


def make_monitor(name="Shop"):
    return Monitor(name=name, url="https://shop.test", alert_email="owner@example.com")


def make_incident(severity="critical", issues=None):
    return Incident(
        monitor_id=1,
        severity=severity,
        affected=issues or ["https://shop.test: Domain name could not be resolved"],
        started_at=utcnow(),
    )


def test_email_not_configured_sends_nothing(monkeypatch):
    monkeypatch.setattr(settings, "smtp_user", "")
    assert notifier.send_email("a@b.com", "Hi", "Body") is False
    assert FakeSMTP.sent == []


def test_email_is_sent():
    assert notifier.send_email("a@b.com", "Hello", "Body text") is True
    message = FakeSMTP.sent[0]
    assert message["To"] == "a@b.com"
    assert message["Subject"] == "Hello"
    assert "Body text" in message.get_content()


def test_newlines_in_subject_are_removed():
    notifier.send_email("a@b.com", "Evil\nBcc: x@y.com", "Body")
    assert "\n" not in FakeSMTP.sent[0]["Subject"]


def test_smtp_error_returns_false_and_does_not_raise():
    FakeSMTP.fail_login = True
    assert notifier.send_email("a@b.com", "Hello", "Body") is False


def test_incident_alert_content():
    assert notifier.send_incident_alert(make_monitor(), make_incident()) is True
    message = FakeSMTP.sent[0]
    assert "[DOWN]" in message["Subject"]
    body = message.get_content()
    assert "https://shop.test" in body
    assert "could not be resolved" in body


def test_degraded_alert_and_recovery_notice():
    monitor = make_monitor()
    incident = make_incident(severity="medium", issues=["/pricing returned HTTP 404"])
    notifier.send_incident_alert(monitor, incident)
    assert "[DEGRADED]" in FakeSMTP.sent[0]["Subject"]

    incident.resolved_at = utcnow()
    notifier.send_recovery_notice(monitor, incident)
    assert "[RECOVERED]" in FakeSMTP.sent[1]["Subject"]

def test_alert_with_ai_analysis_has_cause_and_steps():
    incident = make_incident()
    incident.summary = "The site cannot be reached."
    incident.probable_cause = "The domain does not resolve."
    incident.suggestions = ["Check the domain registration", "Check the DNS records"]
    notifier.send_incident_alert(make_monitor(), incident)
    body = FakeSMTP.sent[0].get_content()
    assert "LIKELY CAUSE" in body
    assert "does not resolve" in body
    assert "1. Check the domain registration" in body
    assert "automatically" in body

def test_from_header_is_well_formed():
    notifier.send_email("a@b.com", "Hi", "Body")
    assert FakeSMTP.sent[0]["From"] == "Website Monitor <monitor@example.com>"


def test_smtp_from_must_be_only_an_address():
    with pytest.raises(ValueError):
        Settings(
            admin_password="a",
            jwt_secret="b",
            smtp_from="Website Monitor x@y.com",
            _env_file=None,
        )
def test_brevo_is_used_when_configured(monkeypatch):
    calls = []

    class Resp:
        status_code = 201
        text = "ok"

    monkeypatch.setattr(settings, "brevo_api_key", "key")
    monkeypatch.setattr(settings, "brevo_sender_email", "me@example.com")
    monkeypatch.setattr(notifier.httpx, "post", lambda url, **kw: calls.append((url, kw)) or Resp())
    assert notifier.send_email("a@b.com", "Hi", "Body") is True
    assert calls[0][0] == "https://api.brevo.com/v3/smtp/email"
    assert calls[0][1]["json"]["to"] == [{"email": "a@b.com"}]
    assert FakeSMTP.sent == []


def test_brevo_error_returns_false(monkeypatch):
    class Resp:
        status_code = 400
        text = "sender invalid"

    monkeypatch.setattr(settings, "brevo_api_key", "key")
    monkeypatch.setattr(settings, "brevo_sender_email", "me@example.com")
    monkeypatch.setattr(notifier.httpx, "post", lambda url, **kw: Resp())
    assert notifier.send_email("a@b.com", "Hi", "Body") is False


def test_postgres_url_is_normalised():
    s = Settings(admin_password="a", jwt_secret="b", database_url="postgres://u:p@h/db", _env_file=None)
    assert s.database_url == "postgresql+psycopg2://u:p@h/db"