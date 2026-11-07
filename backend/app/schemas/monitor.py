from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.config import settings


def _clean_url(value: str) -> str:
    value = value.strip()
    if not value.startswith(("http://", "https://")):
        raise ValueError("URL must start with http:// or https://")
    return value.rstrip("/")


def _clean_paths(values: list[str]) -> list[str]:
    """Accept '/login' or a full URL. Add a leading '/' if missing."""
    cleaned = []
    for v in values:
        v = v.strip()
        if not v:
            continue
        if not v.startswith(("http://", "https://", "/")):
            v = "/" + v
        cleaned.append(v)
    return cleaned


class MonitorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    url: str
    routes: list[str] = Field(default_factory=list, max_length=50)
    api_endpoints: list[str] = Field(default_factory=list, max_length=50)
    alert_email: EmailStr
    interval_minutes: int = Field(default=5, ge=settings.min_interval_minutes, le=1440)
    enabled: bool = True

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        return _clean_url(v)

    @field_validator("routes", "api_endpoints")
    @classmethod
    def validate_paths(cls, v: list[str]) -> list[str]:
        return _clean_paths(v)


class MonitorUpdate(BaseModel):
    """All fields optional: send only what you want to change."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    url: Optional[str] = None
    routes: Optional[list[str]] = Field(default=None, max_length=50)
    api_endpoints: Optional[list[str]] = Field(default=None, max_length=50)
    alert_email: Optional[EmailStr] = None
    interval_minutes: Optional[int] = Field(
        default=None, ge=settings.min_interval_minutes, le=1440
    )
    enabled: Optional[bool] = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        return _clean_url(v) if v is not None else v

    @field_validator("routes", "api_endpoints")
    @classmethod
    def validate_paths(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        return _clean_paths(v) if v is not None else v


class MonitorRead(BaseModel):
    """What the API sends back."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    url: str
    routes: list[str]
    api_endpoints: list[str]
    alert_email: str
    interval_minutes: int
    enabled: bool
    status: str
    last_checked_at: Optional[datetime]
    created_at: datetime