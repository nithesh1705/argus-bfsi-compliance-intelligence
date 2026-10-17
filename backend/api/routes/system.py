"""
ARGUS — System Health & Diagnostics API Routes (backend/api/routes/system.py)

Exposes:
- GET /api/system/health:
  - Live checks for Cloud SQL and Cloud Storage (cheap, local/in-process)
  - Last-known statuses for Vertex AI, File Search, and DLP derived from provider_health
    (zero live LLM pings, zero cost, zero artificial latency)
  - mock_mode badge flag, active model IDs, and Cloud Trace deep link template
- GET /api/system/diagnostics:
  - End-to-end and per-stage latency timings (mean, median, min, max)
"""

import time
import logging
from typing import Dict, Any, List
from fastapi import APIRouter

from backend.core.config import settings
from backend.adapters.database import db_manager
from backend.adapters.storage import get_object_store
from backend.db.repositories.dashboard_repo import get_pipeline_latency_summary

logger = logging.getLogger("argus.api.system")

router = APIRouter(prefix="/system", tags=["System Diagnostics"])


@router.get("/health", response_model=Dict[str, Any])
def get_system_health():
    """
    Returns live health for Cloud SQL & Cloud Storage, and last-known operational
    status for Vertex AI, File Search, and Sensitive Data Protection (DLP).
    """
    # 1. LIVE CHECK: Cloud SQL for MySQL
    t0 = time.time()
    db_status = "HEALTHY"
    db_details = "Connected to Cloud SQL for MySQL"
    try:
        with db_manager.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 AS probe")
                cur.fetchone()
        db_latency = int((time.time() - t0) * 1000)
    except Exception as exc:
        db_status = "UNREACHABLE"
        db_details = str(exc)
        db_latency = int((time.time() - t0) * 1000)

    # 2. LIVE CHECK: Cloud Storage
    t1 = time.time()
    storage_status = "HEALTHY"
    storage_details = f"Storage operational ({'mock' if settings.is_mock() else 'GCS'})"
    try:
        store = get_object_store()
        store.list_objects("calls/incoming")
        storage_latency = int((time.time() - t1) * 1000)
    except Exception as exc:
        storage_status = "DEGRADED"
        storage_details = str(exc)
        storage_latency = int((time.time() - t1) * 1000)

    # 3. LAST-KNOWN STATUSES: Vertex AI, File Search, DLP from provider_health table
    provider_statuses = {}
    try:
        with db_manager.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT dependency_name, status, details, latency_ms FROM provider_health")
                for r in cur.fetchall():
                    provider_statuses[r["dependency_name"]] = {
                        "status": r["status"],
                        "details": r["details"],
                        "latency_ms": r["latency_ms"],
                    }
    except Exception as exc:
        logger.warning(f"Could not read provider_health: {exc}")

    # Build response structure
    return {
        "status": "HEALTHY" if db_status == "HEALTHY" and storage_status == "HEALTHY" else "DEGRADED",
        "mock_mode": settings.is_mock(),
        "provider_mode": settings.PROVIDER_MODE,
        "environment": settings.ENVIRONMENT,
        "project_id": settings.PROJECT_ID,
        "database": {
            "status": "connected" if db_status == "HEALTHY" else "disconnected",
            "latency_ms": db_latency,
            "details": db_details,
        },
        "object_store": {
            "status": "connected" if storage_status == "HEALTHY" else "disconnected",
            "latency_ms": storage_latency,
            "details": storage_details,
        },
        "active_models": {
            "flash": settings.GEMINI_FLASH_MODEL,
            "transcribe": settings.GEMINI_TRANSCRIBE_MODEL,
        },
        "trace_deep_link_template": settings.CLOUD_TRACE_DEEP_LINK_TEMPLATE.format(
            project_id=settings.PROJECT_ID,
            trace_id="{trace_id}"
        ),
        "trace_viewer_url_template": settings.CLOUD_TRACE_DEEP_LINK_TEMPLATE.format(
            project_id=settings.PROJECT_ID,
            trace_id="{trace_id}"
        ),
        "services": {
            "cloud_sql": {
                "name": "Cloud SQL (MySQL 8.0)",
                "status": db_status,
                "latency_ms": db_latency,
                "type": "live_probe",
                "details": db_details,
            },
            "cloud_storage": {
                "name": "Cloud Storage",
                "status": storage_status,
                "latency_ms": storage_latency,
                "type": "live_probe",
                "details": storage_details,
            },
            "vertex_ai": {
                "name": f"Vertex AI ({settings.GEMINI_FLASH_MODEL})",
                "status": provider_statuses.get("Vertex AI", {}).get("status", "HEALTHY"),
                "type": "last_known",
                "details": provider_statuses.get("Vertex AI", {}).get("details", "Ready for forensic inference"),
            },
            "file_search": {
                "name": "Gemini File Search Store",
                "status": provider_statuses.get("Gemini File Search", {}).get("status", "HEALTHY"),
                "type": "last_known",
                "details": provider_statuses.get("Gemini File Search", {}).get("details", f"Strategy: {settings.FS_STRATEGY}"),
            },
            "dlp": {
                "name": "Sensitive Data Protection (DLP)",
                "status": provider_statuses.get("Sensitive Data Protection", {}).get("status", "HEALTHY"),
                "type": "last_known",
                "details": provider_statuses.get("Sensitive Data Protection", {}).get("details", "PII redaction active"),
            },
        }
    }


@router.get("/diagnostics", response_model=Dict[str, Any])
def get_system_diagnostics():
    """Returns latency summaries by pipeline stage and end-to-end metrics."""
    return get_pipeline_latency_summary()
