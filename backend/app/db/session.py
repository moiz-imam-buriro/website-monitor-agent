from collections.abc import Generator
from pathlib import Path
from sqlmodel import Session, SQLModel, create_engine
from app.core.config import settings 
from app.db import models

is_sqlite = settings.database_url.startswith("sqlite")

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if is_sqlite else {},
    pool_pre_ping=not is_sqlite,
    pool_recycle=-1 if is_sqlite else 300,
)

def init_db() -> None:
    """Create the data folder and all tables (safe to run on every start)."""
    if is_sqlite:
        db_file = Path(settings.database_url.replace("sqlite:///", "", 1))
        db_file.parent.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)

def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency: gives each request its own DB session."""
    with Session(engine) as session:
        yield session