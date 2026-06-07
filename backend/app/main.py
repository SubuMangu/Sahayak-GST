"""Sahayak GST — FastAPI application entrypoint (modular monolith, SRS §4)."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import init_db

# When the frontend has been built, serve it from the same origin as the API (single port,
# no CORS) — used by Codespaces and single-port deploys. Build with VITE_API_BASE_URL=/api/v1.
_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
_SERVE_UI = _DIST.is_dir()

DISCLAIMER = (
    "Sahayak GST is an assistive tool. Final responsibility for accuracy and timely filing "
    "rests with the taxpayer. We recommend review by a qualified professional for complex cases."
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # For the MVP we create tables on startup; production uses Alembic migrations.
    await init_db()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description=(
        "AI-Powered GST & Compliance Automation Platform for Indian MSMEs.\n\n"
        f"_{DISCLAIMER}_"
    ),
    lifespan=lifespan,
    docs_url="/docs",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "app": settings.APP_NAME, "region": settings.DATA_REGION}


@app.get("/", include_in_schema=not _SERVE_UI, tags=["system"])
async def root():
    # Serve the SPA shell when the UI is bundled; otherwise return API metadata.
    if _SERVE_UI:
        return FileResponse(_DIST / "index.html")
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs",
        "disclaimer": DISCLAIMER,
    }


# Friendly fallback so unexpected errors don't leak internals (SRS §3.4 input security).
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    if settings.is_dev:
        raise exc
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


# Mount the versioned API.
from app.api.router import api_router  # noqa: E402

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# --- Single-origin static serving (for Codespaces / single-port deploys) ---
# Registered last so the API routes above always take precedence. The catch-all serves real
# static files (favicon, manifest, sw.js, icons) and falls back to the SPA shell for client
# routes like /invoices and /returns.
if _SERVE_UI:
    if (_DIST / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        candidate = _DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_DIST / "index.html")

