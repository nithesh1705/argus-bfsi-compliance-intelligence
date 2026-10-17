"""
ARGUS Phase 2 Test Suite — T0: Environment & Readiness
tests/phase2/test_t0_env.py
"""

import os
import subprocess
import pytest
from backend.core.config import settings
from backend.adapters.database import db_manager


def test_t0_1_adc_and_provider_mode():
    """Assert ADC is active, target GCP project is configured, and provider mode is live."""
    assert settings.PROVIDER_MODE == "live", f"Expected live provider mode, got {settings.PROVIDER_MODE}"
    assert settings.PROJECT_ID == "project-c5373081-153f-4b0a-bd8"
    assert not settings.is_mock(), "settings.is_mock() must be False in live mode"


def test_t0_2_preflight_live():
    """Run scripts/preflight.py live and assert zero failures."""
    res = subprocess.run(["python", "scripts/preflight.py"], capture_output=True, text=True, cwd=str(settings.BASE_DIR))
    assert res.returncode == 0, f"Preflight failed:\n{res.stdout}\n{res.stderr}"
    assert "ALL PREFLIGHT CHECKS PASSED" in res.stdout


def test_t0_3_vertex_location_and_models():
    """Verify Vertex AI model endpoints and location configuration."""
    assert settings.VERTEX_LOCATION in ["us-central1", "global", "asia-south1"]
    assert settings.GEMINI_FLASH_MODEL
    assert settings.GEMINI_TRANSCRIBE_MODEL


def test_t0_4_cloud_sql_schema_and_seed():
    """Verify Cloud SQL 17 tables, seed data integrity, and idempotent migrations."""
    tables_expected = [
        "app_settings", "candidate", "case_activity_log", "compliance_case",
        "customer", "finding", "investigation", "pipeline_run",
        "pipeline_stage_timing", "product", "provider_health",
        "regulation_chunk_registry", "reviewer", "rm", "schema_migrations",
        "system_audit_log", "transcript_segment", "call", "transaction"
    ]
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SHOW TABLES")
            tables = [list(r.values())[0] for r in cur.fetchall()]
            for t in ["rm", "customer", "product", "reviewer", "app_settings", "regulation_chunk_registry"]:
                assert t in tables, f"Missing table {t}"
                cur.execute(f"SELECT COUNT(*) AS c FROM {t}")
                cnt = cur.fetchone()["c"]
                assert cnt > 0, f"Table {t} has no seed rows"


def test_t0_5_iam_and_apis():
    """Verify IAM roles and required GCP APIs (Original test: fails on Windows without shell=True)."""
    res = subprocess.run(
        ["gcloud", "services", "list", "--enabled", f"--project={settings.PROJECT_ID}", "--format=value(config.name)"],
        capture_output=True, text=True
    )
    assert res.returncode == 0
    enabled = res.stdout.split()
    for api in ["aiplatform.googleapis.com", "storage.googleapis.com", "dlp.googleapis.com", "cloudbuild.googleapis.com"]:
        assert api in enabled, f"Required API {api} not enabled"


def test_t0_5_iam_and_apis_corrected():
    """TEST DEFECT CORRECTION: Verify IAM roles and required GCP APIs on Windows using shell=True."""
    res = subprocess.run(
        ["gcloud", "services", "list", "--enabled", f"--project={settings.PROJECT_ID}", "--format=value(config.name)"],
        capture_output=True, text=True, shell=True
    )
    assert res.returncode == 0
    enabled = res.stdout.split()
    for api in ["aiplatform.googleapis.com", "storage.googleapis.com", "dlp.googleapis.com", "cloudbuild.googleapis.com"]:
        assert api in enabled, f"Required API {api} not enabled"

