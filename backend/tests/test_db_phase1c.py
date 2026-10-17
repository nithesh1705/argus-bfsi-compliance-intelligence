"""
ARGUS — Phase 1C Database & Repository Verification Tests (backend/tests/test_db_phase1c.py)
"""

import pytest
from datetime import datetime

from backend.db.repositories.calls_repo import (
    create_or_update_call,
    save_transcript_segments,
    get_call_by_id,
    list_calls,
)
from backend.db.repositories.cases_repo import (
    list_cases,
    get_case_detail,
    update_case_status,
    escalate_case,
    assign_case,
    add_case_note,
    CaseAlreadyResolvedError,
    CaseAlreadyEscalatedError,
    ReviewerNotFoundError,
)
from backend.db.repositories.rm_repo import (
    get_rm_list_with_stats,
    get_rm_detail,
    get_rm_history,
)
from backend.db.repositories.dashboard_repo import (
    get_dashboard_summary,
    get_pipeline_latency_summary,
)
from backend.db.repositories.findings_repo import (
    commit_confirmed_finding,
    list_findings,
)


def test_rm_stats_aggregation():
    rms = get_rm_list_with_stats()
    assert len(rms) >= 5
    first_rm = rms[0]
    assert "rm_id" in first_rm
    assert "risk_score" in first_rm
    assert "total_violations" in first_rm


def test_call_lifecycle_and_segments():
    call_id = "CALL_TEST_RM001_CUST001"
    call_data = {
        "id": call_id,
        "rm_id": "RM001",
        "customer_id": "CUST001",
        "product_id": "PROD005",
        "gcs_uri_incoming": "gs://argus-calls/incoming/test.wav",
        "gcs_uri_archive": None,
        "source_object_generation": "12345",
        "language": "en",
        "duration_s": 95.0,
        "status": "PROCESSED",
        "speaker_mapping_method": "llm",
        "has_violation": False,
        "finding_count": 0,
        "severity": None,
        "date_time": "2026-03-10 10:30:00",
        "provider_used": "mock",
        "is_mock": True,
    }
    saved_id = create_or_update_call(call_data)
    assert saved_id == call_id

    # Add segments
    segments = [
        {"idx": 0, "speaker_label": "Speaker 1", "role": "RM", "start_ms": 0, "end_ms": 4000, "text_original": "Good morning", "text_english": "Good morning"},
        {"idx": 1, "speaker_label": "Speaker 2", "role": "CUSTOMER", "start_ms": 4200, "end_ms": 8000, "text_original": "Hello Arjun", "text_english": "Hello Arjun"},
    ]
    seg_count = save_transcript_segments(call_id, segments)
    assert seg_count == 2

    # Fetch call detail
    fetched = get_call_by_id(call_id)
    assert fetched is not None
    assert fetched["rm_name"] == "Arjun Mehta"
    assert fetched["customer_name"] == "Meena Iyer"
    assert len(fetched["transcript"]) == 2
    assert fetched["transcript"][0]["timestamp_display"] == "00:00"


def test_atomic_finding_and_case_action_lifecycle():
    call_id = "CALL_TEST_RM001_CUST001"
    finding_id = "FND-TEST-001"
    case_id = "CASE_TEST_001"

    finding_data = {
        "finding_id": finding_id,
        "case_id": case_id,
        "call_id": call_id,
        "investigation_id": "INV-TEST-001",
        "regulation_chunk_id": "SEBI_MF_2026_REG_39",
        "citation_label": "SEBI MF Regulations 2026 - Reg 39",
        "source_url": "https://www.sebi.gov.in",
        "page_number": 42,
        "severity": "HIGH",
        "confidence": 0.94,
        "category": "SUITABILITY_MISMATCH",
        "timestamp_start": 20,
        "timestamp_end": 35,
        "quote_original": "I really think you should put at least two lakhs into this.",
        "quote_english": "I really think you should put at least two lakhs into this.",
        "evidence": {"risk_mismatch": True},
        "provider_used": "mock",
        "model": "gemini-3.5-flash",
    }

    # First ensure clean test state and regulation chunk in registry
    from backend.adapters.database import db_manager
    with db_manager.transaction() as cur:
        cur.execute("DELETE FROM compliance_case WHERE case_id = %s", (case_id,))
        cur.execute("DELETE FROM finding WHERE finding_id = %s", (finding_id,))
        cur.execute("""
        INSERT INTO regulation_chunk_registry (
            chunk_id, document_name, clause, citation_label, status, year, source_url, page_number, chunk_text
        ) VALUES (
            'SEBI_MF_2026_REG_39', 'SEBI Mutual Funds Regulations 2026', 'Regulation 39',
            'SEBI MF Regulations 2026 - Reg 39', 'current', 2026, 'https://www.sebi.gov.in', 42,
            'Distributor shall assess the suitability of products before recommending to clients.'
        ) ON DUPLICATE KEY UPDATE chunk_text=VALUES(chunk_text)
        """)

    # Atomic commit
    f_id = commit_confirmed_finding(finding_data)
    assert f_id == finding_id

    # Verify call has_violation was set to True
    call_row = get_call_by_id(call_id)
    assert call_row["has_violation"] == 1
    assert call_row["severity"] == "HIGH"

    # Verify full evidence chain assembly
    case_detail = get_case_detail(case_id)
    assert case_detail is not None
    assert case_detail["status"] == "OPEN"
    assert case_detail["severity"] == "HIGH"
    assert case_detail["citation_label"] == "SEBI MF Regulations 2026 - Reg 39"
    assert case_detail["page_number"] == 42
    assert len(case_detail["activity_log"]) >= 1

    # Test assignment (idempotent)
    assigned = assign_case(case_id, "REV001", "REV002")
    assert assigned["assigned_to"] == "REV002"

    # Test adding a note
    noted = add_case_note(case_id, "REV002", "Investigating customer trade records.")
    assert len(noted["activity_log"]) >= 3

    # Test escalation
    escalated = escalate_case(case_id, "REV002", "High severity suitability breach.")
    assert escalated["escalated"] == 1

    # Test double escalation (MUST raise 409 CaseAlreadyEscalatedError)
    with pytest.raises(CaseAlreadyEscalatedError):
        escalate_case(case_id, "REV002", "Duplicate escalation attempt.")

    # Test resolution
    resolved = update_case_status(case_id, "REV002", "mark_reviewed", "Action taken: RM cautioned.")
    assert resolved["status"] == "RESOLVED"
    assert resolved["resolution_type"] == "CONFIRMED_ACTION_TAKEN"

    # Test resolving already resolved case (MUST raise 409 CaseAlreadyResolvedError)
    with pytest.raises(CaseAlreadyResolvedError):
        update_case_status(case_id, "REV002", "dismiss", "Cannot dismiss already resolved case.")


def test_dashboard_summary_computation():
    summary = get_dashboard_summary()
    assert "total_calls" in summary
    assert "total_findings" in summary
    assert "severity_counts" in summary
    assert "case_status_counts" in summary
    assert "pipeline_latency" in summary
