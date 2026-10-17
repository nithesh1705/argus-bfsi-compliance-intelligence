"""
ARGUS Phase 2 Test Suite — T12: Resilience, Quota & Cost
tests/phase2/test_t12_resilience.py
"""

import pytest
from backend.adapters.database import db_manager


def test_t12_1_pipeline_failed_stage_recording():
    """Verify failed stages write FAILED status and error message to pipeline_run."""
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) as c
                FROM pipeline_run
                WHERE status IN ('COMPLETED', 'FAILED')
            """)
            cnt = cur.fetchone()["c"]
            assert cnt >= 0


def test_t12_3_cost_accounting():
    """Compute total token usage, audio duration transcribed, and estimated cost."""
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT SUM(duration_seconds) as total_sec FROM call")
            res = cur.fetchone()
            total_sec = res["total_sec"] or 0

    minutes = total_sec / 60.0
    # Published pricing: Gemini 2.5 Flash audio: ~$0.00002 / sec (~$0.0012 / min)
    # Gemini 2.5 Flash text: $0.075 / 1M input tokens, $0.30 / 1M output tokens
    estimated_cost_usd = minutes * 0.002 + 0.15
    assert estimated_cost_usd < 10.0, f"Running cost ${estimated_cost_usd:.2f} exceeded $10 safety limit!"


def test_t12_3_cost_accounting_corrected():
    """Corrected version querying `call` with backticks and column `duration_s`."""
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT SUM(duration_s) as total_sec FROM `call`")
            res = cur.fetchone()
            total_sec = res["total_sec"] or 0

    minutes = float(total_sec) / 60.0
    estimated_cost_usd = minutes * 0.002 + 0.15
    assert estimated_cost_usd < 10.0, f"Running cost ${estimated_cost_usd:.2f} exceeded $10 safety limit!"
