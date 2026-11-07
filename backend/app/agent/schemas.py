from typing import Literal

from pydantic import BaseModel, Field, field_validator


class IncidentReport(BaseModel):
    """What the website owner reads: what happened, why, and what to do."""

    summary: str
    probable_cause: str
    severity: Literal["low", "medium", "high", "critical"]
    affected: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"] = "medium"
    ai_generated: bool = True  # False when this is the plain fallback report

    @field_validator("summary", "probable_cause")
    @classmethod
    def _tidy_text(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("must not be empty")
        return value[:600]

    @field_validator("affected", "suggestions")
    @classmethod
    def _tidy_list(cls, values: list[str]) -> list[str]:
        cleaned = [" ".join(str(v).split())[:300] for v in values]
        return [v for v in cleaned if v][:10]


def fallback_report(status: str, issues: list[str]) -> IncidentReport:
    """A plain report built only from the monitor's findings (no AI involved)."""
    first = issues[0] if issues else "A problem was detected on the website"
    extra = f" (and {len(issues) - 1} more problem(s))" if len(issues) > 1 else ""
    return IncidentReport(
        summary=f"{first}{extra}",
        probable_cause=(
            "The cause could not be worked out automatically. "
            "The list of problems below shows what failed."
        ),
        severity="critical" if status == "down" else "medium",
        affected=list(issues),
        suggestions=[
            "Open the affected addresses in a browser to confirm the problem.",
            "Check your hosting provider's status page and your server logs.",
        ],
        confidence="low",
        ai_generated=False,
    )