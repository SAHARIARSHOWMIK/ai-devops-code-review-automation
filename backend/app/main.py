from contextlib import asynccontextmanager
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .api.router import router
from .core.config import get_settings
from .core.database import Base, SessionLocal, engine
from .models import Organization
from .services.demo_seed import seed_demo


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    settings = get_settings()
    if settings.demo_mode:
        with SessionLocal() as db:
            if db.query(Organization).count() == 0:
                seed_demo(db)
    yield


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Repository-aware AI and deterministic pull-request review with human approval and GitHub publishing.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:4173", "http://localhost:5173"],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|172\.\d+\.\d+\.\d+)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api")

frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if os.getenv("SERVE_FRONTEND", "false").lower() == "true" and frontend_dist.exists():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
else:
    @app.get("/")
    def root() -> dict:
        return {"name": settings.app_name, "docs": "/docs", "health": "/api/health"}
