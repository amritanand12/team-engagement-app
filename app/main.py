from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure project root is in sys.path when running as a script (e.g. `python app/main.py`)
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import init_db, session_scope
from app.routers import admin, auth, health, superadmin, webhooks
from app.seed import seed_superadmin
from app.services.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
settings = get_settings()

uploads_path = Path("uploads")
uploads_path.mkdir(parents=True, exist_ok=True)
(uploads_path / "photos").mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with session_scope() as db:
        seed_superadmin(db)
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="Team Engagement Service",
    description="Automated birthday & work-anniversary notifications, driven by static templates and HRMS data.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

from fastapi import HTTPException
from fastapi.responses import FileResponse, RedirectResponse

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(superadmin.router)
app.include_router(webhooks.router)

dashboard_dist = Path("dashboard/dist")
if dashboard_dist.exists() and (dashboard_dist / "index.html").exists():
    if (dashboard_dist / "assets").exists():
        app.mount("/assets", StaticFiles(directory=dashboard_dist / "assets"), name="dashboard_assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        if full_path.startswith(("admin", "auth", "health", "docs", "openapi.json", "uploads", "superadmin")):
            raise HTTPException(status_code=404, detail="Not Found")
        file_path = dashboard_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(dashboard_dist / "index.html")
else:
    @app.get("/", include_in_schema=False)
    def root_redirect():
        return RedirectResponse(url="/docs")



if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

