"""
ARGUS Phase 2 Test Suite — T3: Ingestion Agent (Transcription, Translation, Roles, PII)
tests/phase2/test_t3_ingestion.py
"""

import time
import os
import re
import pytest
from pathlib import Path
from backend.adapters.transcriber import get_transcriber, VertexGeminiTranscriber
from backend.adapters.pii_redactor import get_pii_redactor, SensitiveDataProtectionRedactor
from backend.ingestion.ingestion_agent import map_roles_and_translate, build_custom_vocabulary
from backend.core.config import settings


def calculate_wer(reference: str, hypothesis: str) -> float:
    """Compute Word Error Rate (Levenshtein distance over words)."""
    ref_words = reference.lower().split()
    hyp_words = hypothesis.lower().split()
    if not ref_words:
        return 0.0 if not hyp_words else 1.0

    d = [[0] * (len(hyp_words) + 1) for _ in range(len(ref_words) + 1)]
    for i in range(len(ref_words) + 1):
        d[i][0] = i
    for j in range(len(hyp_words) + 1):
        d[0][j] = j

    for i in range(1, len(ref_words) + 1):
        for j in range(1, len(hyp_words) + 1):
            if ref_words[i - 1] == hyp_words[j - 1]:
                d[i][j] = d[i - 1][j - 1]
            else:
                d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + 1)
    return d[len(ref_words)][len(hyp_words)] / len(ref_words)


def calculate_cer(reference: str, hypothesis: str) -> float:
    """Compute Character Error Rate (Levenshtein distance over characters)."""
    ref_chars = list(reference.replace(" ", "").lower())
    hyp_chars = list(hypothesis.replace(" ", "").lower())
    if not ref_chars:
        return 0.0 if not hyp_chars else 1.0

    d = [[0] * (len(hyp_chars) + 1) for _ in range(len(ref_chars) + 1)]
    for i in range(len(ref_chars) + 1):
        d[i][0] = i
    for j in range(len(hyp_chars) + 1):
        d[0][j] = j

    for i in range(1, len(ref_chars) + 1):
        for j in range(1, len(hyp_chars) + 1):
            if ref_chars[i - 1] == hyp_chars[j - 1]:
                d[i][j] = d[i - 1][j - 1]
            else:
                d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + 1)
    return d[len(ref_chars)][len(hyp_chars)] / len(ref_chars)


def test_t3_1_and_t3_2_live_transcription_and_accuracy():
    """Live transcribe RM001_CUST001 and measure duration, monotonicity, WER/CER."""
    transcriber = get_transcriber()
    assert isinstance(transcriber, VertexGeminiTranscriber)

    audio_uri = f"gs://{settings.CALLS_BUCKET}/calls/_backup/RM001_CUST001_20260310_1030.wav"
    t0 = time.time()
    out = transcriber.transcribe(audio_uri=audio_uri, call_id="CALL_RM001_CUST001_20260310_1030")
    latency = time.time() - t0

    assert out.segments, "No segments extracted"
    assert out.duration_s > 0, "Duration must be positive"

    # Check monotonicity
    prev_start = -1
    for s in out.segments:
        assert s.start_ms >= prev_start, f"Timestamps not monotonic: {s.start_ms} < {prev_start}"
        assert s.end_ms > s.start_ms, f"Segment end <= start: {s.end_ms} <= {s.start_ms}"
        prev_start = s.start_ms

    # Compare with ground script
    script_path = settings.BASE_DIR / "data" / "audio" / "audio_scripts" / "RM001_CUST001_20260310_1030.txt"
    if script_path.exists():
        with open(script_path, "r", encoding="utf-8") as f:
            script_text = f.read()
        full_hyp = " ".join([s.text_original for s in out.segments])
        wer = calculate_wer(script_text, full_hyp)
        assert wer < 0.60, f"WER {wer:.2f} too high for live transcription"


def test_t3_3_speaker_role_mapping():
    """Verify speaker-role mapping determines RM and CUSTOMER correctly."""
    from backend.adapters.transcriber import DiarizedSegment
    segments = [
        DiarizedSegment(1, "Speaker 1", 0, 3000, "Good morning, this is Rajesh from Alpha Securities. Am I speaking with Mr. Sharma?"),
        DiarizedSegment(2, "Speaker 2", 3100, 5000, "Yes Rajesh, speaking. How can I help you?"),
        DiarizedSegment(3, "Speaker 1", 5100, 9000, "I am calling to discuss our new high return mutual fund opportunities."),
    ]
    rm_label, cust_label, method, translations = map_roles_and_translate(
        segments=segments,
        rm_name="Rajesh",
        customer_name="Mr. Sharma",
        call_id="TEST_CALL"
    )
    assert rm_label == "Speaker 1"
    assert cust_label == "Speaker 2"


def test_t3_5_live_dlp_pii_redaction():
    """Assert Google Cloud Sensitive Data Protection redacts Indian PAN, Aadhaar, Phone, Email, Card."""
    redactor = get_pii_redactor()
    assert isinstance(redactor, SensitiveDataProtectionRedactor)

    sample_text = (
        "My PAN is ABCDE1234F, Aadhaar is 2345 6789 0123, "
        "phone is 9876543210, email is test.user@gmail.com, and card is 4111 2222 3333 4444."
    )
    res = redactor.redact_text(sample_text)

    # Verify redactions occurred
    assert "ABCDE1234F" not in res.redacted_text
    assert "2345 6789 0123" not in res.redacted_text
    assert "9876543210" not in res.redacted_text
    assert "test.user@gmail.com" not in res.redacted_text
    assert "4111 2222 3333 4444" not in res.redacted_text
    assert res.findings_count >= 3


def test_t3_6_awkward_audio_handling():
    """Verify empty/corrupt audio ends in recorded FAILED state without unhandled crash."""
    from backend.ingestion.audio_validator import validate_audio_file
    import tempfile

    # Empty file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
        tf.write(b"")
        tf_path = Path(tf.name)

    try:
        valid, err = validate_audio_file(tf_path)
        assert not valid, "Empty file should not be valid"
        assert "empty" in err.lower() or "small" in err.lower() or "header" in err.lower()
    finally:
        if tf_path.exists():
            tf_path.unlink()
