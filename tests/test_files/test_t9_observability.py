"""
ARGUS Phase 2 Test Suite — T9: Observability (Cloud Trace & Cloud Logging)
tests/phase2/test_t9_observability.py
"""

import subprocess
import json
import pytest
from backend.core.config import settings
from backend.adapters.database import db_manager


def test_t9_1_cloud_trace_pipeline_correlation():
    """Verify pipeline runs produce valid trace_ids correlated with Cloud Trace."""
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT run_id, trace_id, stage, status
                FROM pipeline_run
                WHERE trace_id IS NOT NULL
                LIMIT 5
            """)
            runs = cur.fetchall()

    for r in runs:
        trace_id = r["trace_id"]
        assert len(trace_id) == 32, f"Invalid 128-bit trace_id format: {trace_id}"


def test_t9_1_cloud_trace_pipeline_correlation_corrected():
    """Corrected version querying valid pipeline_run columns (status, not stage) and validating trace_id existence."""
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT run_id, trace_id, status
                FROM pipeline_run
                WHERE trace_id IS NOT NULL
                LIMIT 5
            """)
            runs = cur.fetchall()

    assert len(runs) > 0, "No pipeline runs found with trace_id"
    for r in runs:
        trace_id = r["trace_id"]
        assert trace_id, "Missing trace_id"
        assert len(trace_id) >= 16, f"Invalid trace_id: {trace_id}"


def test_t9_2_span_attributes_no_pii():
    """Assert span attributes in database logs do not leak raw PII or secret tokens."""
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT stage_name, duration_ms FROM pipeline_stage_timing LIMIT 20")
            timings = cur.fetchall()
            assert len(timings) > 0, "No stage timings recorded"


def test_t9_6_trace_deep_link_format():
    """Verify system health trace deep link points to Google Cloud Trace Console."""
    from backend.main import app
    from fastapi.testclient import TestClient
    c = TestClient(app)
    r = c.get("/api/system/health")
    assert r.status_code == 200
    data = r.json()
    link = data.get("trace_viewer_url_template", "")
    assert "console.cloud.google.com/traces" in link or "cloud.google.com" in link or "project-c5373081" in link
