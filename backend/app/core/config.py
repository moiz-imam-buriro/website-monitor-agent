from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root
BASE_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # app
    app_name: str = "Website Monitor Agent"

    # Security (required: app will not start without them)
    admin_password: str
    jwt_secret: str
    jwt_expire_minutes: int = 60 * 24

    # database
    database_url: str = f"sqlite:///{BASE_DIR / 'data' / 'monitor.db'}"

    # LLM
    groq_api_key: str = ""
    llm_model: str = "openai/gpt-oss-20b"
    llm_timeout_seconds: int = 60
    llm_max_tokens: int = 3000  # gpt-oss counts its "thinking" tokens in this limit
    agent_max_steps: int = 14  # stops the agent loop (about 6 tool calls)

    # email smtp
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""  # the address only; empty means "use SMTP_USER"
    smtp_from_name: str = "Website Monitor"
    smtp_timeout_seconds: int = 15
    brevo_api_key: str = ""
    brevo_sender_email: str = ""

    # monitoring limits 
    request_timeout_seconds: int = 10
    min_interval_minutes: int = 5
    max_alerts_per_hour: int = 3
    max_agent_runs_per_day: int = 20
    allow_private_targets: bool = False  # True only on your own PC, for testing
    recheck_delay_seconds: int = 10  # wait before confirming a failed check
    check_retention_days: int = 30  # how long to keep check history
    scheduler_enabled: bool = True  # set False when testing the API
    agent_enabled: bool = True  # kill switch: False means plain alerts only

    # dashboard (browser) access
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @field_validator("smtp_from")
    @classmethod
    def _smtp_from_is_only_an_address(cls, value: str) -> str:
        value = value.strip()
        if value and (" " in value or "<" in value or ">" in value or "@" not in value):
            raise ValueError(
                "SMTP_FROM must be only an email address. "
                "Put the display name in SMTP_FROM_NAME instead."
            )
        return value
    
    @field_validator("database_url")
    @classmethod
    def _fix_database_url(cls, value: str) -> str:
        for old in ("postgres://", "postgresql://"):
            if value.startswith(old):
                return "postgresql+psycopg2://" + value[len(old):]
        return value
    
    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()