"""
ARGUS Phase 2 Test Suite — T10: Security
tests/phase2/test_t10_security.py
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.adapters.database import db_manager


client = TestClient(app)


def test_t10_1_oidc_rejection_without_token():
    """Assert POST /events/gcs without valid Google OIDC Bearer token is rejected."""
    # Unauthenticated call
    r = client.post("/events/gcs", json={"message": {"data": "eyJkdW1teSI6ICJkYXRhIn0="}})
    # Must be 401 Unauthorized or 403 Forbidden
    assert r.status_code in [401, 403], f"Expected 401/403 without OIDC token, got {r.status_code}"

    # Invalid Bearer token
    r = client.post(
        "/events/gcs",
        headers={"Authorization": "Bearer invalid_fake_oidc_token"},
        json={"message": {"data": "eyJkdW1teSI6ICJkYXRhIn0="}}
    )
    assert r.status_code in [401, 403]


def test_t10_2_input_injection_attacks():
    """Assert SQL injection and path traversal payloads do not cause internal server errors or data leaks."""
    malicious_inputs = [
        "' OR '1'='1",
        "'; DROP TABLE compliance_case; --",
        "../../../../etc/passwd",
        "..\\..\\Windows\\System32\\calc.exe",
        "<script>alert(1)</script>",
        "\x00\x00\x00\x00",
        "A" * 10000,  # Buffer overflow / oversized query
    ]

    for attack in malicious_inputs:
        # Call search parameter
        r = client.get(f"/api/calls?search={attack}")
        assert r.status_code in [200, 400, 422], f"Vulnerability detected for input '{attack}': {r.status_code}"

        # Call ID path parameter
        r = client.get(f"/api/calls/{attack}")
        assert r.status_code in [404, 400, 422]


def test_t10_2_input_injection_attacks_corrected():
    """Corrected version using properly encoded params dict to avoid client-side HTTPX urlparse aborts on raw unescaped null bytes."""
    malicious_inputs = [
        "' OR '1'='1",
        "'; DROP TABLE compliance_case; --",
        "../../../../etc/passwd",
        "..\\..\\Windows\\System32\\calc.exe",
        "<script>alert(1)</script>",
        "%00%00%00%00",
        "A" * 10000,
    ]

    for attack in malicious_inputs:
        # Call search parameter passed safely through query params
        r = client.get("/api/calls", params={"search": attack})
        assert r.status_code in [200, 400, 422], f"Vulnerability detected for input '{attack}': {r.status_code}"

        # Call ID path parameter
        r = client.get(f"/api/calls/{attack}")
        assert r.status_code in [404, 400, 422]


def test_t10_4_secrets_hygiene():
    """Verify raw DB passwords or API keys are never returned by API or exposed in health check."""
    r = client.get("/api/system/health")
    assert r.status_code == 200
    text = r.text
    assert "qwerty12345" not in text, "Raw database password leaked in health API!"
    assert "password" not in text.lower() or "password_protected" in text.lower()


def test_t10_6_dlp_stored_transcript_sanitization():
    """Scan all stored transcript segments in Cloud SQL for unredacted Indian PAN or Aadhaar."""
    import re
    pan_regex = re.compile(r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b')
    aadhaar_regex = re.compile(r'\b[2-9]{1}[0-9]{3}\s[0-9]{4}\s[0-9]{4}\b')

    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT segment_id, redacted_text FROM transcript_segment LIMIT 500")
            rows = cur.fetchall()

    for r in rows:
        txt = r["redacted_text"] or ""
        assert not pan_regex.search(txt), f"Unredacted PAN found in segment {r['segment_id']}: {txt}"
        assert not aadhaar_regex.search(txt), f"Unredacted Aadhaar found in segment {r['segment_id']}: {txt}"


def test_t10_6_dlp_stored_transcript_sanitization_corrected():
    """Corrected version querying text_original and text_english where DLP redacted transcripts are stored."""
    import re
    pan_regex = re.compile(r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b')
    aadhaar_regex = re.compile(r'\b[2-9]{1}[0-9]{3}\s[0-9]{4}\s[0-9]{4}\b')

    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT segment_id, text_original, text_english FROM transcript_segment LIMIT 500")
            rows = cur.fetchall()

    assert len(rows) > 0, "No transcript segments found to inspect"
    for r in rows:
        txt_orig = r["text_original"] or ""
        txt_en = r["text_english"] or ""
        assert not pan_regex.search(txt_orig), f"Unredacted PAN found in text_original of segment {r['segment_id']}"
        assert not pan_regex.search(txt_en), f"Unredacted PAN found in text_english of segment {r['segment_id']}"
        assert not aadhaar_regex.search(txt_orig), f"Unredacted Aadhaar found in text_original of segment {r['segment_id']}"
        assert not aadhaar_regex.search(txt_en), f"Unredacted Aadhaar found in text_english of segment {r['segment_id']}"
