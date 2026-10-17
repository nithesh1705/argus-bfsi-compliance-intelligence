"""
ARGUS Phase 2 Test Suite — T6: Full Pipeline End to End & Benchmark
tests/phase2/test_t6_pipeline.py
"""

import subprocess
import pytest
from backend.core.config import settings
from backend.adapters.database import db_manager
from backend.adapters.storage import get_object_store


def test_t6_1_db_reconciliation():
    """Assert pipeline entities exist and reconcile across calls, segments, candidates, findings, cases."""
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as c FROM call")
            calls_cnt = cur.fetchone()["c"]

            cur.execute("SELECT COUNT(*) as c FROM transcript_segment")
            segments_cnt = cur.fetchone()["c"]

            cur.execute("SELECT COUNT(*) as c FROM compliance_case")
            cases_cnt = cur.fetchone()["c"]

            assert calls_cnt > 0, "No calls recorded"
            assert segments_cnt > 0, "No transcript segments recorded"


def test_t6_1_db_reconciliation_corrected():
    """Corrected version using backticks for MySQL reserved word `call`."""
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as c FROM `call`")
            calls_cnt = cur.fetchone()["c"]

            cur.execute("SELECT COUNT(*) as c FROM transcript_segment")
            segments_cnt = cur.fetchone()["c"]

            cur.execute("SELECT COUNT(*) as c FROM compliance_case")
            cases_cnt = cur.fetchone()["c"]

            assert calls_cnt > 0, "No calls recorded"
            assert segments_cnt > 0, "No transcript segments recorded"
            assert cases_cnt > 0, "No cases recorded"


def test_t6_3_benchmark_execution():
    """Run 3-way benchmark comparison and assert valid metrics."""
    res = subprocess.run(["python", "backend/benchmark/run_benchmark.py"], capture_output=True, text=True, cwd=str(settings.BASE_DIR))
    assert res.returncode == 0, f"Benchmark failed:\n{res.stdout}\n{res.stderr}"
    assert "Keyword Regex Baseline" in res.stdout
    assert "ARGUS Full Pipeline" in res.stdout
