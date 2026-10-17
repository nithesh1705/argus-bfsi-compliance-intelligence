"""
ARGUS — Phase 1D Ingestion Agent Verification Tests (backend/tests/test_ingestion_phase1d.py)
"""

import pytest

from backend.ingestion.filename_parser import parse_and_validate_filename, FilenameValidationError
from backend.ingestion.ingestion_agent import process_audio_ingestion
from backend.db.repositories.calls_repo import get_call_by_id


def test_filename_parser_valid():
    info = parse_and_validate_filename("RM001_CUST001_20260310_1030.wav")
    assert info.rm_id == "RM001"
    assert info.customer_id == "CUST001"
    assert info.call_id == "CALL_RM001_CUST001_20260310_1030"
    assert info.rm_name == "Arjun Mehta"
    assert info.customer_name == "Meena Iyer"


def test_filename_parser_invalid_pattern():
    with pytest.raises(FilenameValidationError) as exc_info:
        parse_and_validate_filename("invalid_filename_format.wav")
    assert exc_info.value.reason == "FILENAME_PATTERN_MISMATCH"


def test_filename_parser_unknown_rm():
    with pytest.raises(FilenameValidationError) as exc_info:
        parse_and_validate_filename("RM999_CUST001_20260310_1030.wav")
    assert exc_info.value.reason == "RM_NOT_FOUND"


def test_ingestion_agent_pipeline():
    call_id = "CALL_RM001_CUST001_20260310_1030"
    res = process_audio_ingestion(
        audio_uri="mock://calls/incoming/RM001_CUST001_20260310_1030.wav",
        call_id=call_id,
        rm_id="RM001",
        customer_id="CUST001",
        product_id="PROD005",
    )

    assert res["call_id"] == call_id
    assert res["status"] == "INGESTED"
    assert res["segments_count"] > 0

    # Verify call in Cloud SQL
    call = get_call_by_id(call_id)
    assert call is not None
    assert call["status"] == "INGESTED"
    assert len(call["transcript"]) > 0

    # Verify that speakers were mapped to RM and CUSTOMER roles
    roles = {s["speaker"] for s in call["transcript"]}
    assert "RM" in roles or "CUSTOMER" in roles

    # Verify timestamps are populated and sorted
    first_seg = call["transcript"][0]
    assert first_seg["start_time"] == 0.0
    assert first_seg["end_time"] > 0.0
