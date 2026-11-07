import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.deps import require_admin
from app.api.routes import agent, auth, health, incidents, monitors
from app.core.config import settings
from app.db.session import init_db
from app.monitoring.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logging.getLogger("apscheduler").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # create tables on startup
    start_scheduler()  # the agent now runs in the background, 24/7
    yield
    stop_scheduler()

app = FastAPI(title = settings.app_name, lifespan = lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Public routes
app.include_router(health.router)
app.include_router(auth.router)

# Protected routes: every route inside needs a valid admin token
protected = [Depends(require_admin)]
app.include_router(monitors.router, dependencies=protected)
app.include_router(incidents.router, dependencies=protected)
app.include_router(agent.router, dependencies=protected)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if (STATIC_DIR / "index.html").is_file():
    if (STATIC_DIR / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_dashboard(full_path: str):
        candidate = (STATIC_DIR / full_path).resolve()
        if full_path and candidate.is_file() and STATIC_DIR.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(STATIC_DIR / "index.html")