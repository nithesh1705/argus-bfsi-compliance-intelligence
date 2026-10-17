"""
ARGUS — Calls Repository (backend/db/repositories/calls_repo.py)

Manages database persistence and queries for call recordings and transcripts,
replacing the legacy Elasticsearch 'calls' index with SQL.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from backend.adapters.database import db_manager

logger = logging.getLogger("argus.db.calls")


def create_or_update_call(call_data: Dict[str, Any]) -> str:
    """Inserts or updates a call record."""
    sql = """
    INSERT INTO `call` (
        id, rm_id, customer_id, product_id, gcs_uri_incoming, gcs_uri_archive,
        source_object_generation, language, duration_s, status, speaker_mapping_method,
        has_violation, finding_count, severity, date_time, provider_used, is_mock
    ) VALUES (
        %(id)s, %(rm_id)s, %(customer_id)s, %(product_id)s, %(gcs_uri_incoming)s, %(gcs_uri_archive)s,
        %(source_object_generation)s, %(language)s, %(duration_s)s, %(status)s, %(speaker_mapping_method)s,
        %(has_violation)s, %(finding_count)s, %(severity)s, %(date_time)s, %(provider_used)s, %(is_mock)s
    ) ON DUPLICATE KEY UPDATE
        status = VALUES(status),
        gcs_uri_archive = COALESCE(VALUES(gcs_uri_archive), gcs_uri_archive),
        duration_s = VALUES(duration_s),
        has_violation = VALUES(has_violation),
        finding_count = VALUES(finding_count),
        severity = VALUES(severity),
        updated_at = CURRENT_TIMESTAMP
    """
    with db_manager.transaction() as cursor:
        cursor.execute(sql, call_data)
    return call_data["id"]


def save_transcript_segments(call_id: str, segments: List[Dict[str, Any]]) -> int:
    """Batch inserts transcript segments for a call."""
    delete_sql = "DELETE FROM transcript_segment WHERE call_id = %s"
    insert_sql = """
    INSERT INTO transcript_segment (
        call_id, idx, speaker_label, role, start_ms, end_ms, text_original, text_english, is_violation
    ) VALUES (
        %(call_id)s, %(idx)s, %(speaker_label)s, %(role)s, %(start_ms)s, %(end_ms)s, %(text_original)s, %(text_english)s, %(is_violation)s
    )
    """
    rows = []
    for idx, s in enumerate(segments):
        rows.append({
            "call_id": call_id,
            "idx": idx,
            "speaker_label": s.get("speaker_label", f"Speaker {idx % 2 + 1}"),
            "role": s.get("role", "RM" if idx % 2 == 0 else "CUSTOMER"),
            "start_ms": s.get("start_ms", 0),
            "end_ms": s.get("end_ms", 0),
            "text_original": s.get("text_original", ""),
            "text_english": s.get("text_english", s.get("text_original", "")),
            "is_violation": s.get("is_violation", False),
        })

    with db_manager.transaction() as cursor:
        cursor.execute(delete_sql, (call_id,))
        if rows:
            cursor.executemany(insert_sql, rows)
    return len(rows)


def get_call_by_id(call_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve full call detail including RM, Customer and transcript segments."""
    call_sql = """
    SELECT 
        c.*,
        r.full_name AS rm_name,
        r.branch AS rm_branch,
        cust.full_name AS customer_name,
        cust.risk_profile AS customer_risk_profile,
        cust.investment_experience AS customer_experience
    FROM `call` c
    LEFT JOIN rm r ON c.rm_id = r.rm_id
    LEFT JOIN customer cust ON c.customer_id = cust.customer_id
    WHERE c.id = %s
    """
    segments_sql = """
    SELECT 
        segment_id AS id,
        idx,
        speaker_label,
        role AS speaker,
        start_ms,
        end_ms,
        ROUND(start_ms / 1000.0, 2) AS start_time,
        ROUND(end_ms / 1000.0, 2) AS end_time,
        text_original,
        text_english AS text,
        is_violation
    FROM transcript_segment
    WHERE call_id = %s
    ORDER BY idx ASC
    """
    cases_sql = """
    SELECT 
        cc.case_id,
        cc.finding_id,
        cc.call_id,
        cc.rm_id,
        cc.customer_id,
        cc.category,
        cc.severity,
        cc.status,
        cc.escalated,
        cc.assigned_to,
        f.confidence,
        f.quote_english,
        f.quote_original,
        f.citation_label,
        DATE_FORMAT(cc.created_at, '%%Y-%%m-%%dT%%H:%%i:%%sZ') AS created_at
    FROM compliance_case cc
    LEFT JOIN finding f ON cc.finding_id = f.finding_id
    WHERE cc.call_id = %s
    ORDER BY cc.created_at DESC
    """
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(call_sql, (call_id,))
            call_row = cur.fetchone()
            if not call_row:
                return None
            if not call_row.get("call_id"):
                call_row["call_id"] = call_row.get("id")

            cur.execute(segments_sql, (call_id,))
            segments = cur.fetchall()

            # Format timestamp_display for each segment (e.g. "01:24")
            for seg in segments:
                s_secs = int(seg.get("start_time") or 0)
                m, s = divmod(s_secs, 60)
                seg["timestamp_display"] = f"{m:02d}:{s:02d}"

            cur.execute(cases_sql, (call_id,))
            cases = cur.fetchall()
            for c in cases:
                if c.get("confidence") is not None:
                    try:
                        c["confidence"] = float(c["confidence"])
                    except Exception:
                        pass

            call_row["transcript"] = segments
            call_row["transcript_segments"] = segments
            call_row["cases"] = cases
            if cases and not call_row.get("case_id"):
                call_row["case_id"] = cases[0]["case_id"]
            call_row["audio_url"] = f"/api/calls/{call_id}/audio"

            # Query real stage timings from pipeline_stage_timing
            timing_sql = """
            SELECT stage_name, duration_ms, start_time, end_time, status
            FROM pipeline_stage_timing
            WHERE call_id = %s
            ORDER BY id ASC
            """
            cur.execute(timing_sql, (call_id,))
            timings = cur.fetchall()

            ingest_sec = None
            detect_sec = None
            invest_sec = None
            archive_sec = None
            for t in timings:
                sname = (t.get("stage_name") or "").lower()
                d_sec = round((t.get("duration_ms") or 0) / 1000.0, 1)
                if "ingest" in sname:
                    ingest_sec = d_sec
                    if t.get("start_time"):
                        call_row["processing_started_at"] = t["start_time"].isoformat()
                    if t.get("end_time"):
                        call_row["indexed_at"] = t["end_time"].isoformat()
                elif "detect" in sname:
                    detect_sec = d_sec
                    if t.get("end_time"):
                        call_row["detection_completed_at"] = t["end_time"].isoformat()
                elif "invest" in sname:
                    invest_sec = d_sec
                    if t.get("end_time"):
                        call_row["investigation_completed_at"] = t["end_time"].isoformat()
                elif "archive" in sname:
                    archive_sec = d_sec

            call_row["ingest_duration_s"] = ingest_sec
            call_row["detect_duration_s"] = detect_sec
            call_row["invest_duration_s"] = invest_sec
            call_row["archive_duration_s"] = archive_sec

            # Query pipeline_run for end-to-end duration
            run_sql = """
            SELECT total_duration_ms, start_time, end_time
            FROM pipeline_run
            WHERE call_id = %s AND status = 'COMPLETED'
            ORDER BY start_time DESC
            LIMIT 1
            """
            cur.execute(run_sql, (call_id,))
            run_row = cur.fetchone()
            if run_row and run_row.get("total_duration_ms"):
                call_row["e2e_duration_s"] = round(run_row["total_duration_ms"] / 1000.0, 1)
            elif ingest_sec is not None and detect_sec is not None and invest_sec is not None:
                call_row["e2e_duration_s"] = round(ingest_sec + detect_sec + invest_sec + (archive_sec or 0), 1)
            else:
                call_row["e2e_duration_s"] = None

            return call_row


def list_calls(
    rm_id: Optional[str] = None,
    customer_id: Optional[str] = None,
    severity: Optional[str] = None,
    status_filter: Optional[str] = None,
    has_violation: Optional[bool] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> Dict[str, Any]:
    """Retrieve paginated calls with filters (replaces Elasticsearch calls query)."""
    where_clauses = ["1=1"]
    params: Dict[str, Any] = {"limit": limit, "offset": offset}

    if rm_id:
        where_clauses.append("c.rm_id = %(rm_id)s")
        params["rm_id"] = rm_id
    if customer_id:
        where_clauses.append("c.customer_id = %(customer_id)s")
        params["customer_id"] = customer_id
    if severity:
        where_clauses.append("c.severity = %(severity)s")
        params["severity"] = severity.upper()
    if has_violation is not None:
        where_clauses.append("c.has_violation = %(has_violation)s")
        params["has_violation"] = has_violation

    if status_filter:
        s_upper = status_filter.upper()
        if s_upper in ("COMPLETED", "PROCESSED", "PENDING", "FAILED", "RECEIVED"):
            where_clauses.append("c.status = %(status_filter)s")
            params["status_filter"] = s_upper
        elif s_upper == "VIOLATION":
            where_clauses.append("c.has_violation = TRUE")
        elif s_upper == "CLEAN":
            where_clauses.append("c.has_violation = FALSE")

    if start_date:
        where_clauses.append("c.date_time >= %(start_date)s")
        params["start_date"] = start_date
    if end_date:
        where_clauses.append("c.date_time <= %(end_date)s")
        params["end_date"] = end_date

    where_sql = " AND ".join(where_clauses)

    count_sql = f"SELECT COUNT(*) AS total FROM `call` c WHERE {where_sql}"
    query_sql = f"""
    SELECT 
        c.id AS call_id,
        c.rm_id,
        r.full_name AS rm_name,
        c.customer_id,
        cust.full_name AS customer_name,
        c.duration_s,
        CONCAT(FLOOR(c.duration_s / 60), 'm ', FLOOR(MOD(c.duration_s, 60)), 's') AS duration,
        DATE_FORMAT(c.date_time, '%%Y-%%m-%%dT%%H:%%i:%%sZ') AS date_time,
        c.status AS processing_status,
        c.has_violation,
        c.finding_count,
        c.severity,
        CONCAT('/api/calls/', c.id, '/audio') AS audio_url
    FROM `call` c
    LEFT JOIN rm r ON c.rm_id = r.rm_id
    LEFT JOIN customer cust ON c.customer_id = cust.customer_id
    WHERE {where_sql}
    ORDER BY c.date_time DESC
    LIMIT %(limit)s OFFSET %(offset)s
    """

    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(count_sql, params)
            total = cur.fetchone()["total"]

            cur.execute(query_sql, params)
            items = cur.fetchall()

    return {"total": total, "items": items}
