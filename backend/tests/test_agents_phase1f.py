"""
ARGUS — Phase 1F Detection & Investigation Agents Tests (backend/tests/test_agents_phase1f.py)
"""

import pytest

from backend.ingestion.ingestion_agent import process_audio_ingestion
from backend.agents.detection_agent import run_detection
from backend.agents.investigation_agent import (
    run_investigation_for_candidate,
    run_investigation_for_call,
)
from backend.adapters.database import db_manager
from backend.db.repositories.cases_repo import get_case_detail


def test_detection_agent_flow():
    call_id = "CALL_RM001_CUST001_20260310_1030"
    # Ensure call is ingested
    process_audio_ingestion(
        audio_uri="mock://calls/incoming/RM001_CUST001_20260310_1030.wav",
        call_id=call_id,
        rm_id="RM001",
        customer_id="CUST001",
        product_id="PROD005",
    )

    candidates = run_detection(call_id)
    assert len(candidates) > 0
    first = candidates[0]
    assert "candidate_id" in first
    assert first["category"] in ("SUITABILITY_MISMATCH", "GUARANTEED_RETURN", "MISSING_RISK_DISCLOSURE")
    assert first["quote_english"] != ""
    assert len(first["retrieved_chunk_ids"]) > 0

    # Verify staged into MySQL candidate table
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS c FROM candidate WHERE call_id = %s", (call_id,))
            count = cur.fetchone()["c"]
            assert count >= len(candidates)


def test_investigation_guardrail_no_citation():
    candidate = {
        "candidate_id": "CAND-TEST-NOCITE",
        "call_id": "CALL_RM001_CUST001_20260310_1030",
        "category": "",
        "severity_hint": "HIGH",
        "start_ms": 1000,
        "end_ms": 2000,
        "quote_english": "test quote",
        "quote_original": "test quote",
        "rationale": "test",
    }
    res = run_investigation_for_candidate(
        candidate=candidate,
        call_context={},
        retrieved_passages=[],
        segments=[]
    )
    # Because category is unfindable, should trigger Guardrail 1
    assert "DISMISSED" in res["outcome"]


def test_investigation_confirmed_outcome_and_audit():
    call_id = "CALL_RM001_CUST001_20260310_1030"
    results = run_investigation_for_call(call_id)
    assert len(results) > 0

    # Check investigation table audit row
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT outcome, reasoning FROM investigation WHERE call_id = %s", (call_id,))
            inv_rows = cur.fetchall()
            assert len(inv_rows) > 0

    # If any confirmed, verify case exists
    confirmed = [r for r in results if r.get("outcome") == "CONFIRMED"]
    if confirmed:
        case_id = confirmed[0]["case_id"]
        detail = get_case_detail(case_id)
        assert detail is not None
        assert detail["status"] == "OPEN"
        assert detail["citation_label"] != ""
