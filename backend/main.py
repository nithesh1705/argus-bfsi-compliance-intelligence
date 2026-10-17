"""
ARGUS — Backend API Application Entrypoint (backend/main.py)

FastAPI application configuring:
- CORS middleware with configured origins
- Cloud SQL database & repositories
- Pub/Sub Eventarc GCS finalize endpoint
- Case workflow state machine and 409 exception handlers
- Read-only investigative AI chat assistant
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.core.config import settings

# Load environment
ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(ENV_PATH)

logger = logging.getLogger("argus.api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

from backend.api.routes import (
    dashboard, calls, cases, documents,
    settings as settings_route, chat, system,
    auth, rm, events, benchmark, observability,
    admin,
)
from backend.db.repositories.cases_repo import (
    CaseNotFoundError,
    CaseAlreadyResolvedError,
    CaseAlreadyEscalatedError,
    ReviewerNotFoundError,
)

app = FastAPI(
    title="ARGUS Compliance Intelligence Platform API",
    description="Backend API and forensic compliance workflow engine for ARGUS",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# CORS Configuration
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"https?://.*",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Structured Exception Handlers (State Machine 409 Conflicts & Errors)
# ---------------------------------------------------------------------------

@app.exception_handler(CaseAlreadyResolvedError)
async def case_already_resolved_handler(request: Request, exc: CaseAlreadyResolvedError):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": "CASE_ALREADY_RESOLVED",
            "message": str(exc),
            "case_id": exc.case_id,
        },
    )


@app.exception_handler(CaseAlreadyEscalatedError)
async def case_already_escalated_handler(request: Request, exc: CaseAlreadyEscalatedError):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": "CASE_ALREADY_ESCALATED",
            "message": str(exc),
            "case_id": exc.case_id,
        },
    )


@app.exception_handler(CaseNotFoundError)
async def case_not_found_handler(request: Request, exc: CaseNotFoundError):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "CASE_NOT_FOUND",
            "message": str(exc),
            "case_id": exc.case_id,
        },
    )


@app.exception_handler(ReviewerNotFoundError)
async def reviewer_not_found_handler(request: Request, exc: ReviewerNotFoundError):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "REVIEWER_NOT_FOUND",
            "message": str(exc),
            "reviewer_id": exc.reviewer_id,
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if isinstance(exc.detail, dict):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP_ERROR",
            "message": exc.detail,
            "status_code": exc.status_code,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Invalid request parameters or payload.",
            "details": exc.errors(),
        },
    )


# ---------------------------------------------------------------------------
# API Routes Inclusion
# ---------------------------------------------------------------------------

API_PREFIX = "/api"

# Eventarc & pipeline triggers mounted at root and API
app.include_router(events.router)

app.include_router(dashboard.router, prefix=API_PREFIX)
app.include_router(calls.router, prefix=API_PREFIX)
app.include_router(cases.router, prefix=API_PREFIX)
app.include_router(documents.router, prefix=API_PREFIX)
app.include_router(documents.regulations_router, prefix=API_PREFIX)
app.include_router(settings_route.router, prefix=API_PREFIX)
app.include_router(chat.router, prefix=API_PREFIX)
app.include_router(system.router, prefix=API_PREFIX)
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(rm.router, prefix=API_PREFIX)
app.include_router(benchmark.router, prefix=API_PREFIX)
app.include_router(observability.router, prefix=API_PREFIX)
app.include_router(admin.router, prefix=API_PREFIX)


@app.on_event("startup")
def on_startup():
    """Startup initialization banner and safety verification."""
    if settings.is_mock():
        logger.info("=" * 60)
        logger.info("  ARGUS STARTUP BANNER: RUNNING IN MOCK MODE (OFFLINE)")
        logger.info(f"  Flash Model: {settings.GEMINI_FLASH_MODEL}")
        logger.info(f"  Transcribe Model: {settings.GEMINI_TRANSCRIBE_MODEL}")
        logger.info("  External Google services use deterministic adapters.")
        logger.info("=" * 60)
    else:
        logger.info(f"[Startup] ARGUS running in LIVE mode on GCP project '{settings.PROJECT_ID}'")


@app.get("/", tags=["Health"])
def root():
    """Root endpoint for probe checks and service discovery."""
    return {
        "status": "online",
        "service": "ARGUS Compliance Intelligence Platform API",
        "version": "1.0.0",
        "health": "/health",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
@app.get("/api/health", tags=["Health"])
def health_check():
    """Service health and connectivity probe."""
    return {
        "status": "ok",
        "service": "argus-backend",
        "version": "1.0.0",
        "mock_mode": settings.is_mock(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
