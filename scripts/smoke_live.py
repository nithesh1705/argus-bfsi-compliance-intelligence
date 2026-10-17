"""
ARGUS — Live Smoke Test Script (scripts/smoke_live.py)

Executes a single audio recording end-to-end through the surveillance pipeline:
1. Validates audio naming convention
2. Ingestion & Diarized Speech-to-Text (Gemini Transcribe)
3. Sensitive Data Protection / PII Redaction (DLP)
4. Regulatory Candidate Detection (Gemini Flash)
5. Grounded Statutory Retrieval (Gemini File Search)
6. Forensic Investigation & Evidence Chain Assembly with 4 Hard Guardrails
7. Atomic Cloud SQL Transaction
8. Object Movement to Archive

Prints a stage-by-stage execution report with millisecond timings and
the assembled Evidence Chain if a violation is detected.
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import Dict, Any

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.core.config import settings
from backend.adapters.database import db_manager
from backend.adapters.storage import get_object_store
from backend.ingestion.pipeline_runner import run_pipeline_for_object
from backend.db.repositories.cases_repo import get_case_detail

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("argus.smoke_live")


def run_smoke_test(audio_filename: str):
    print("\n" + "=" * 75)
    print("        ARGUS SURVEILLANCE PIPELINE — END-TO-END SMOKE TEST")
    print(f"        Audio Target: {audio_filename}")
    print(f"        Provider Mode: {'MOCK (Offline)' if settings.is_mock() else 'LIVE (GCP Vertex AI)'}")
    print("=" * 75)

    store = get_object_store()
    incoming_key = f"calls/incoming/{audio_filename}"

    # Ensure audio exists in incoming storage
    try:
        store.read_bytes(incoming_key)
    except Exception:
        # If already archived or in data/audio/audio_scripts, place synthetic file
        logger.warning(f"Audio file '{incoming_key}' not found in incoming storage. Preparing file...")
        stem = Path(audio_filename).stem
        script_file = PROJECT_ROOT / "data" / "audio" / "audio_scripts" / f"{stem}.txt"
        if script_file.exists():
            store.upload_bytes(incoming_key, b"SYNTHETIC_WAV_FOR_SMOKE_TEST\n", content_type="audio/wav")
            print(f"  + Uploaded mock test audio into {incoming_key}")
        else:
            print(f"  [ERROR] Cannot find script or audio file for {audio_filename}")
            return False

    print("\n[Pipeline Execution] Dispatching call to pipeline runner...\n")
    result = run_pipeline_for_object(audio_filename)

    if result.get("status") not in ("COMPLETED", "ALREADY_PROCESSED"):
        print(f"\n[FAIL] Pipeline failed for {audio_filename}: {result}")
        return False

    call_id = result.get("call_id")
    print(f"[Pipeline Execution] Call processing finished. Call ID: {call_id}")

    # Fetch stage timings from Cloud SQL
    timing_sql = """
    SELECT stage_name, duration_ms, status 
    FROM pipeline_stage_timing 
    WHERE call_id = %s 
    ORDER BY id ASC
    """
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(timing_sql, (call_id,))
            stages = cur.fetchall()

            cur.execute("SELECT has_violation, finding_count, severity FROM `call` WHERE id = %s", (call_id,))
            call_info = cur.fetchone()

            cur.execute("SELECT case_id FROM compliance_case WHERE call_id = %s", (call_id,))
            case_row = cur.fetchone()

    # Print Stage-by-Stage Table
    print("\n" + "-" * 75)
    print("  STAGE-BY-STAGE EXECUTION BREAKDOWN")
    print("-" * 75)
    print(f"  {'Stage Name':<38} {'Status':<15} {'Duration':<12}")
    print("-" * 75)

    total_pipeline_ms = 0
    for s in stages:
        total_pipeline_ms += s["duration_ms"]
        print(f"  {s['stage_name']:<38} {s['status']:<15} {s['duration_ms']:>6} ms")

    print("-" * 75)
    print(f"  {'Total Recorded Latency':<38} {'':<15} {total_pipeline_ms:>6} ms")
    print("-" * 75)

    # Print Findings / Evidence Chain
    has_viol = bool(call_info and call_info.get("has_violation"))
    sev = call_info.get("severity") if call_info else "CLEAN"

    print(f"\n[Compliance Outcome] Violation Detected: {has_viol} | Severity: {sev}")

    if has_viol and case_row:
        case_id = case_row["case_id"]
        case_data = get_case_detail(case_id)
        if case_data:
            print("\n" + "=" * 75)
            print("                 ASSEMBLED EVIDENCE CHAIN")
            print("=" * 75)
            print(f"  Case ID:                {case_id}")
            print(f"  Call ID:                {call_id}")
            print(f"  Finding ID:             {case_data.get('finding_id')}")
            print(f"  Category:               {case_data.get('category')}")
            print(f"  Severity Assessment:    {case_data.get('severity')}")
            print(f"  Model Confidence:       {case_data.get('confidence')}")
            print(f"  Audio Moment:           {case_data.get('timestamp_start')}s -> {case_data.get('timestamp_end')}s")
            print(f"  Verbatim Quote:         \"{case_data.get('quote')}\"")
            print(f"  Statutory Citation:     {case_data.get('citation_label')}")
            print(f"  Authoritative URL:      {case_data.get('source_url')}")
            print(f"  Page Number:            {case_data.get('page_number')}")
            print(f"  Forensic Reasoning:     {case_data.get('reasoning')}")
            print("=" * 75)

    print("\n[SUCCESS] End-to-end smoke test completed successfully.\n")
    return True


def main():
    parser = argparse.ArgumentParser(description="ARGUS Live Smoke Test Runner")
    parser.add_argument(
        "--audio",
        default="RM001_CUST001_20260310_1030.wav",
        help="Call audio filename (e.g. RM001_CUST001_20260310_1030.wav)"
    )
    args = parser.parse_args()
    success = run_smoke_test(args.audio)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
