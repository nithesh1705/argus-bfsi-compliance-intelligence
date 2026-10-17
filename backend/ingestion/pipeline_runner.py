"""
ARGUS — Pipeline Runner (backend/ingestion/pipeline_runner.py)

Orchestrates the end-to-end compliance intelligence pipeline for a call:
1. File validation & stability check
2. Stage Ingestion: gemini-3.5-transcribe
3. Stage Translation & Role Mapping: gemini-3.5-flash
4. Stage DLP Redaction: Sensitive Data Protection
5. Stage Detection: gemini-3.5-flash candidate identification
6. Stage Retrieval: Gemini File Search statutory clause grounding
7. Stage Investigation: gemini-3.5-flash forensic reasoning & hard guardrails
8. Stage Persist: Single MySQL transaction commit
9. Stage Archive: Move audio object to calls/archive/

Tracks stage transitions and timings in pipeline_run and pipeline_stage_timing.
Enforces idempotency using (bucket/object/generation).
"""

import time
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

from backend.core.config import settings
from backend.adapters.storage import get_object_store
from backend.adapters.database import db_manager
from backend.ingestion.filename_parser import parse_and_validate_filename, FilenameValidationError
from backend.ingestion.ingestion_agent import process_audio_ingestion
from backend.agents.detection_agent import run_detection
from backend.agents.investigation_agent import run_investigation_for_call
from backend.db.repositories.calls_repo import create_or_update_call, get_call_by_id

logger = logging.getLogger("argus.pipeline.runner")


class PipelineStageTracker:
    def __init__(self, run_id: str, call_id: str):
        self.run_id = run_id
        self.call_id = call_id
        self.stage_timings = []

    def record_stage(self, stage_name: str, start_time: datetime, end_time: datetime, status: str = "COMPLETED"):
        duration_ms = int((end_time - start_time).total_seconds() * 1000)
        sql = """
        INSERT INTO pipeline_stage_timing (run_id, call_id, stage_name, start_time, end_time, duration_ms, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        try:
            with db_manager.transaction() as cur:
                cur.execute(sql, (self.run_id, self.call_id, stage_name, start_time, end_time, duration_ms, status))
            self.stage_timings.append({"stage": stage_name, "duration_ms": duration_ms, "status": status})
        except Exception as exc:
            logger.warning(f"Could not record pipeline stage timing: {exc}")


def run_pipeline_for_object(
    object_name: str,
    bucket_name: Optional[str] = None,
    generation: str = "1",
    trace_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executes the ARGUS pipeline for a given call recording in storage.
    Idempotent: Re-delivered events with the same bucket/object/generation will not create duplicates.
    """
    bucket = bucket_name or settings.CALLS_BUCKET
    trace = trace_id or f"trace-{uuid.uuid4().hex[:16]}"
    run_id = f"RUN-{uuid.uuid4().hex[:12]}"
    store = get_object_store()

    # Step 0: Check idempotency in database
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, status, source_object_generation FROM `call` WHERE gcs_uri_incoming LIKE %s AND source_object_generation = %s",
                (f"%{object_name}%", generation)
            )
            existing = cur.fetchone()
            if existing and existing["status"] == "COMPLETED":
                logger.info(f"[Pipeline] Call object {object_name} (gen {generation}) already processed. Skipping re-run.")
                return {"status": "ALREADY_PROCESSED", "call_id": existing["id"]}

    # Parse and validate filename
    try:
        file_info = parse_and_validate_filename(object_name)
        call_id = file_info.call_id
        rm_id = file_info.rm_id
        customer_id = file_info.customer_id
    except FilenameValidationError as fve:
        logger.error(f"[Pipeline] Filename validation rejected for {object_name}: {fve.reason}")
        # Record permanently failed call row so Pub/Sub does not redeliver in storm
        failed_call_id = f"CALL_FAILED_{object_name.replace('.', '_')}"
        create_or_update_call({
            "id": failed_call_id,
            "rm_id": "RM001",
            "customer_id": "CUST001",
            "product_id": None,
            "gcs_uri_incoming": store.get_uri(f"calls/incoming/{object_name}"),
            "gcs_uri_archive": None,
            "source_object_generation": generation,
            "language": "en",
            "duration_s": 0.0,
            "status": "FAILED(validation)",
            "speaker_mapping_method": "none",
            "has_violation": False,
            "finding_count": 0,
            "severity": None,
            "date_time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "provider_used": "mock" if settings.is_mock() else "vertex_ai",
            "is_mock": settings.is_mock(),
        })
        return {"status": "FAILED", "reason": fve.reason, "message": str(fve)}

    # Initialize call record and pipeline run in database
    start_run_time = datetime.now(timezone.utc)
    create_or_update_call({
        "id": call_id,
        "rm_id": rm_id,
        "customer_id": customer_id,
        "product_id": None,
        "gcs_uri_incoming": f"calls/incoming/{object_name}",
        "gcs_uri_archive": None,
        "source_object_generation": generation,
        "language": "en",
        "duration_s": 0.0,
        "status": "RECEIVED",
        "speaker_mapping_method": "llm",
        "has_violation": False,
        "finding_count": 0,
        "severity": None,
        "date_time": file_info.date_time,
        "provider_used": "mock" if settings.is_mock() else "vertex_ai",
        "is_mock": settings.is_mock(),
    })

    init_run_sql = """
    INSERT INTO pipeline_run (run_id, call_id, trace_id, status, source_object, start_time)
    VALUES (%s, %s, %s, 'RECEIVED', %s, %s)
    """
    with db_manager.transaction() as cur:
        cur.execute(init_run_sql, (run_id, call_id, trace, object_name, start_run_time))

    tracker = PipelineStageTracker(run_id, call_id)
    audio_incoming_key = f"calls/incoming/{object_name}"
    audio_incoming_uri = store.get_uri(audio_incoming_key)

    try:
        # Stage 1: Ingestion, Translation, Role Mapping & DLP Redaction
        t0 = datetime.now(timezone.utc)
        ingest_res = process_audio_ingestion(
            audio_uri=audio_incoming_uri,
            call_id=call_id,
            rm_id=rm_id,
            customer_id=customer_id,
            product_id=None,
            source_generation=generation,
        )
        t1 = datetime.now(timezone.utc)
        tracker.record_stage("ingestion.transcribe_and_redact", t0, t1, "COMPLETED")

        # Stage 2: Candidate Detection
        t2 = datetime.now(timezone.utc)
        candidates = run_detection(call_id)
        t3 = datetime.now(timezone.utc)
        tracker.record_stage("detection.run", t2, t3, "COMPLETED")

        # Stage 3: Regulatory Retrieval & Forensic Investigation
        t4 = datetime.now(timezone.utc)
        investigation_results = run_investigation_for_call(call_id)
        t5 = datetime.now(timezone.utc)
        tracker.record_stage("investigation.run", t4, t5, "COMPLETED")

        # Stage 4: Archive Move
        t6 = datetime.now(timezone.utc)
        archive_key = f"calls/archive/{object_name}"
        store.copy_object(audio_incoming_key, archive_key)
        store.delete_object(audio_incoming_key)
        archive_uri = store.get_uri(archive_key)

        # Update call record with archive URI and status COMPLETED
        with db_manager.transaction() as cur:
            cur.execute(
                "UPDATE `call` SET status = 'COMPLETED', gcs_uri_archive = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                (archive_uri, call_id)
            )
        t7 = datetime.now(timezone.utc)
        tracker.record_stage("archive.move", t6, t7, "COMPLETED")

        # Finalize run
        end_run_time = datetime.now(timezone.utc)
        total_duration = int((end_run_time - start_run_time).total_seconds() * 1000)
        with db_manager.transaction() as cur:
            cur.execute(
                "UPDATE pipeline_run SET status = 'COMPLETED', end_time = %s, total_duration_ms = %s WHERE run_id = %s",
                (end_run_time, total_duration, run_id)
            )

        logger.info(f"[Pipeline] Successfully processed call {call_id} in {total_duration}ms")
        return {
            "status": "COMPLETED",
            "call_id": call_id,
            "run_id": run_id,
            "trace_id": trace,
            "total_duration_ms": total_duration,
            "candidates_count": len(candidates),
            "investigations_count": len(investigation_results),
            "archive_uri": archive_uri,
        }

    except Exception as exc:
        logger.exception(f"[Pipeline] Pipeline execution failed on call {call_id}: {exc}")
        end_run_time = datetime.now(timezone.utc)
        total_duration = int((end_run_time - start_run_time).total_seconds() * 1000)
        err_msg = str(exc)

        with db_manager.transaction() as cur:
            cur.execute(
                "UPDATE pipeline_run SET status = 'FAILED', end_time = %s, total_duration_ms = %s, error_details = %s WHERE run_id = %s",
                (end_run_time, total_duration, err_msg, run_id)
            )
            cur.execute(
                "UPDATE `call` SET status = 'FAILED', updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                (call_id,)
            )

        return {
            "status": "FAILED",
            "call_id": call_id,
            "run_id": run_id,
            "error": err_msg,
        }
