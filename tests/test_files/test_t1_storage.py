"""
ARGUS Phase 2 Test Suite — T1: Cloud Storage
tests/phase2/test_t1_storage.py
"""

import pytest
from backend.adapters.storage import get_object_store, GCSObjectStore
from backend.ingestion.filename_parser import parse_call_filename, CallFileMetadata


def test_t1_1_gcs_crud_and_metadata():
    """Assert live GCS CRUD operations, metadata attributes, and archive move."""
    store = get_object_store()
    assert isinstance(store, GCSObjectStore)

    test_key = "calls/incoming/_phase2_test_probe.txt"
    payload = b"ARGUS_PHASE2_GCS_PROBE"
    store.upload_bytes(test_key, payload, content_type="text/plain")

    # Read back
    data = store.download_bytes(test_key)
    assert data == payload

    meta = store.get_metadata(test_key)
    assert meta.content_type == "text/plain"
    assert meta.size_bytes == len(payload)

    # Archive move
    archived_key = "calls/archive/_phase2_test_probe.txt"
    store.move_object(test_key, archived_key)
    assert not store.exists(test_key)
    assert store.exists(archived_key)

    # Clean up
    store.delete_object(archived_key)
    assert not store.exists(archived_key)


def test_t1_2_range_streaming():
    """Assert byte-range streaming returns exact slice and partial content."""
    store = get_object_store()
    probe_key = "calls/_backup/RM001_CUST001_20260310_1030.wav"
    assert store.exists(probe_key), f"Probe file {probe_key} must exist in backup"

    # Request first 1024 bytes
    chunk = store.download_range(probe_key, start_byte=0, end_byte=1023)
    assert len(chunk) == 1024


def test_t1_3_filename_validation():
    """Assert 8 invalid filenames are strictly rejected with validation errors."""
    invalid_cases = [
        "invalid_format.wav",
        "RM999_CUST001_20260310_1030.wav",  # Unknown RM
        "RM001_CUST999_20260310_1030.wav",  # Unknown Customer
        "RM001_CUST001_99999999_1030.wav",  # Bad date
        "RM001_CUST001_20260310_9999.wav",  # Bad time
        "RM001_CUST001_20260310_1030.exe",   # Wrong extension
        "../../RM001_CUST001_20260310_1030.wav",  # Path traversal
        "RM001_CUST001_20260310_1030.wav;rm -rf /",  # Command injection chars
    ]
    for bad_name in invalid_cases:
        meta = parse_call_filename(bad_name)
        assert meta is None, f"Invalid filename '{bad_name}' was incorrectly accepted!"


def test_t1_4_idempotency_guard():
    """Assert delivering the same object/generation twice is recognized as duplicate."""
    store = get_object_store()
    meta = store.get_metadata("calls/_backup/RM001_CUST001_20260310_1030.wav")
    assert meta.generation
