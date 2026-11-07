import logging
import smtplib
import httpx
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import formatdate, make_msgid, formataddr

from app.core.config import settings
from app.db.models import Incident, Monitor

logger = logging.getLogger(__name__)

MAX_ISSUES_IN_EMAIL = 15


# helpers
def _one_line(text: str) -> str:
    """Newlines in an email header would let a user inject extra headers."""
    return " ".join(text.split())


def _naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _fmt_time(dt: datetime | None) -> str:
    if dt is None:
        return "unknown"
    return _naive_utc(dt).strftime("%Y-%m-%d %H:%M UTC")


def _duration(start: datetime, end: datetime) -> str:
    minutes = int((_naive_utc(end) - _naive_utc(start)).total_seconds() // 60)
    if minutes < 1:
        return "less than a minute"
    if minutes < 60:
        return f"{minutes} minute(s)"
    hours, rest = divmod(minutes, 60)
    return f"{hours} hour(s) {rest} minute(s)"

def brevo_configured() -> bool:
    return bool(settings.brevo_api_key and settings.brevo_sender_email)


def email_configured() -> bool:
    return brevo_configured() or bool(settings.smtp_user and settings.smtp_password)


def _send_brevo(to: str, subject: str, body: str) -> bool:
    try:
        response = httpx.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={"api-key": settings.brevo_api_key, "accept": "application/json"},
            json={
                "sender": {
                    "name": settings.smtp_from_name,
                    "email": settings.brevo_sender_email,
                },
                "to": [{"email": to}],
                "subject": _one_line(subject),
                "textContent": body,
            },
            timeout=settings.smtp_timeout_seconds,
        )
    except httpx.HTTPError as e:
        logger.error("Brevo request failed: %s", e)
        return False
    if response.status_code >= 300:
        logger.error("Brevo refused the email (HTTP %s): %s", response.status_code, response.text[:300])
        return False
    logger.info("Email sent to %s via Brevo: %s", to, _one_line(subject))
    return True

# sending
def send_email(to: str, subject: str, body: str) -> bool:
    """Send a plain-text email. Never raises. Returns True only if it was sent."""
    if not email_configured():
        logger.warning("Email not configured (SMTP_USER / SMTP_PASSWORD): skipped")
        return False
    if brevo_configured():
        return _send_brevo(to, subject, body)

    try:
        message = EmailMessage()
        sender = settings.smtp_from or settings.smtp_user
        message["From"] = formataddr((settings.smtp_from_name, sender))
        message["To"] = to
        message["Subject"] = _one_line(subject)
        message["Date"] = formatdate()
        message["Message-ID"] = make_msgid()
        message.set_content(body)

        use_ssl = settings.smtp_port == 465
        smtp_class = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
        with smtp_class(
            settings.smtp_host,
            settings.smtp_port,
            timeout=settings.smtp_timeout_seconds,
        ) as server:
            if not use_ssl:
                server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(message)
    except (smtplib.SMTPException, OSError, ValueError) as e:
        logger.error("Could not send email to %s: %s", to, e)
        return False

    logger.info("Email sent to %s: %s", to, _one_line(subject))
    return True


# messages
def send_incident_alert(monitor: Monitor, incident: Incident) -> bool:
    down = incident.severity == "critical"
    label = "DOWN" if down else "DEGRADED"
    meaning = (
        "the main page is not working"
        if down
        else "the main page works, but parts of the site are broken"
    )
    explained = bool(incident.probable_cause)  # the agent wrote an analysis

    issues = list(incident.affected or [])
    lines = [f"  - {issue}" for issue in issues[:MAX_ISSUES_IN_EMAIL]]
    if len(issues) > MAX_ISSUES_IN_EMAIL:
        lines.append(f"  - ... and {len(issues) - MAX_ISSUES_IN_EMAIL} more")

    parts = [
        f"Website:   {monitor.name}",
        f"Address:   {monitor.url}",
        f"Status:    {label} ({meaning})",
        f"Detected:  {_fmt_time(incident.started_at)}",
        "",
    ]
    if explained:
        parts += [
            "WHAT HAPPENED",
            f"  {incident.summary}",
            "",
            "LIKELY CAUSE",
            f"  {incident.probable_cause}",
            "",
        ]
        steps = list(incident.suggestions or [])
        if steps:
            parts += ["WHAT TO DO", *[f"  {n}. {s}" for n, s in enumerate(steps, 1)], ""]
        parts += ["TECHNICAL DETAILS", *lines, ""]
    else:
        parts += ["What was found:", *lines, ""]

    parts += [
        f"We check every {monitor.interval_minutes} minute(s) and will email you",
        "again when the problem is fixed.",
        "",
    ]
    if explained:
        parts += [
            "The analysis above was written automatically by an AI assistant.",
            "It can be wrong, so please verify before acting on it.",
            "",
        ]
    parts.append("-- Website Monitor Agent (automatic message)")

    return send_email(
        monitor.alert_email, f"[{label}] {monitor.name} has a problem", "\n".join(parts)
    )

def send_recovery_notice(monitor: Monitor, incident: Incident) -> bool:
    ended = incident.resolved_at
    lasted = _duration(incident.started_at, ended) if ended else "unknown"
    body = "\n".join(
        [
            f"Website:   {monitor.name}",
            f"Address:   {monitor.url}",
            "Status:    WORKING AGAIN",
            f"Problem started:  {_fmt_time(incident.started_at)}",
            f"Fixed:            {_fmt_time(ended)}",
            f"Lasted:           {lasted}",
            "",
            "-- Website Monitor Agent (automatic message)",
        ]
    )
    return send_email(
        monitor.alert_email, f"[RECOVERED] {monitor.name} is working again", body
    )