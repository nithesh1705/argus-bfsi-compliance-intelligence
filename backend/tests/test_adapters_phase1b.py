"""
ARGUS — Phase 1B Adapter Verification Tests (backend/tests/test_adapters_phase1b.py)
"""

import pytest
from pathlib import Path

from backend.core.config import settings
from backend.adapters.storage import LocalObjectStore, get_object_store
from backend.adapters.pii_redactor import RegexPiiRedactor, get_pii_redactor
from backend.adapters.transcriber import MockTranscriber, get_transcriber
from backend.adapters.retriever import MockRegulationRetriever, get_regulation_retriever
from backend.adapters.llm import MockLLMClient, get_llm_client


def test_settings_initialization():
    assert settings.PROVIDER_MODE == "mock"
    assert settings.is_mock() is True
    assert settings.GEMINI_FLASH_MODEL == "gemini-3.5-flash"
    assert settings.GEMINI_TRANSCRIBE_MODEL in ("gemini-3.5-transcribe", "gemini-3.5-transcribe-preview")


def test_local_object_store(tmp_path):
    store = LocalObjectStore(root_dir=tmp_path)
    
    # Upload bytes
    test_key = "calls/incoming/test_call.wav"
    data = b"RIFF....WAVEfmt ...."
    uri = store.upload_bytes(test_key, data)
    assert "mock://" in uri

    # List objects
    objs = store.list_objects("calls/incoming")
    assert any("test_call.wav" in o for o in objs)

    # Read bytes
    read_data = store.read_bytes(test_key)
    assert read_data == data

    # Read range
    range_data = store.read_range(test_key, start=0, length=4)
    assert range_data == b"RIFF"

    # Copy object
    archive_key = "calls/archive/test_call.wav"
    store.copy_object(test_key, archive_key)
    assert store.read_bytes(archive_key) == data

    # Delete object
    assert store.delete_object(test_key) is True
    assert len(store.list_objects("calls/incoming")) == 0


def test_pii_redactor():
    redactor = RegexPiiRedactor()
    sample_text = (
        "Hello, my PAN is ABCDE1234F and Aadhaar is 2345 6789 0123. "
        "You can call me at 9876543210 or email test.user@example.com."
    )
    res = redactor.redact_text(sample_text)
    assert "[PAN]" in res.redacted_text
    assert "ABCDE1234F" not in res.redacted_text
    assert "[AADHAAR]" in res.redacted_text
    assert "2345 6789 0123" not in res.redacted_text
    assert "[PHONE]" in res.redacted_text
    assert "9876543210" not in res.redacted_text
    assert "[EMAIL]" in res.redacted_text
    assert "test.user@example.com" not in res.redacted_text
    assert res.findings_count >= 4


def test_mock_transcriber():
    transcriber = MockTranscriber()
    output = transcriber.transcribe("mock://calls/incoming/RM001_CUST001_20260310_1030.wav", "CALL_RM001_CUST001_20260310_1030")
    assert output.call_id == "CALL_RM001_CUST001_20260310_1030"
    assert len(output.segments) > 0
    first_seg = output.segments[0]
    assert first_seg.speaker_label in ("Speaker 1", "Speaker 2")
    assert first_seg.start_ms == 0
    assert "Arjun" in first_seg.text_original or "Mrs. Iyer" in first_seg.text_original
    assert len(first_seg.words) > 0


def test_mock_retriever():
    retriever = MockRegulationRetriever()
    passages = retriever.search_regulations("guaranteed return assurance", status="current", limit=3)
    assert len(passages) > 0
    first = passages[0]
    assert first.chunk_id != ""
    assert first.page_number >= 1
    assert "http" in first.source_url
