"""
ARGUS — Compliance Cases Repository (backend/db/repositories/cases_repo.py)

Manages compliance case workflow, full Evidence Chain assembly, and atomic
state machine transitions with strict conflict (409) validation.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from backend.adapters.database import db_manager

logger = logging.getLogger("argus.db.cases")


class CaseNotFoundError(Exception):
    def __init__(self, case_id: str):
        self.case_id = case_id
        super().__init__(f"Compliance case '{case_id}' not found.")


class CaseAlreadyResolvedError(Exception):
    def __init__(self, case_id: str):
        self.case_id = case_id
        super().__init__(f"Case '{case_id}' is already in RESOLVED status.")


class CaseAlreadyEscalatedError(Exception):
    def __init__(self, case_id: str):
        self.case_id = case_id
        super().__init__(f"Case '{case_id}' has already been escalated to the committee.")


class ReviewerNotFoundError(Exception):
    def __init__(self, reviewer_id: str):
        self.reviewer_id = reviewer_id
        super().__init__(f"Reviewer with ID '{reviewer_id}' not found.")


def get_current_confidence_threshold() -> float:
    """Read the stored confidence_threshold from app_settings (default 0.75)."""
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT setting_value FROM app_settings WHERE setting_key = 'confidence_threshold'")
            row = cur.fetchone()
            if row and row.get("setting_value"):
                try:
                    return float(row["setting_value"])
                except (ValueError, TypeError):
                    pass
    return 0.75


def list_cases(
    status_filter: Optional[str] = None,
    severity: Optional[str] = None,
    rm_id: Optional[str] = None,
    call_id: Optional[str] = None,
    needs_review: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0
) -> Dict[str, Any]:
    """
    List cases with filtering and computed needs_review flag.
    """
    threshold = get_current_confidence_threshold()
    where_clauses = ["1=1"]
    params: Dict[str, Any] = {"limit": limit, "offset": offset, "threshold": threshold}

    if status_filter:
        where_clauses.append("cc.status = %(status_filter)s")
        params["status_filter"] = status_filter.upper()
    if severity:
        where_clauses.append("cc.severity = %(severity)s")
        params["severity"] = severity.upper()
    if rm_id:
        where_clauses.append("cc.rm_id = %(rm_id)s")
        params["rm_id"] = rm_id
    if call_id:
        where_clauses.append("cc.call_id = %(call_id)s")
        params["call_id"] = call_id

    # If needs_review filter is provided, filter by confidence compared to threshold
    if needs_review is not None:
        if needs_review:
            where_clauses.append("f.confidence < %(threshold)s")
        else:
            where_clauses.append("f.confidence >= %(threshold)s")

    where_sql = " AND ".join(where_clauses)

    count_sql = f"""
    SELECT COUNT(*) AS total
    FROM compliance_case cc
    LEFT JOIN finding f ON cc.finding_id = f.finding_id
    WHERE {where_sql}
    """

    query_sql = f"""
    SELECT 
        cc.case_id,
        cc.finding_id,
        cc.call_id,
        cc.rm_id,
        r.full_name AS rm_name,
        cc.customer_id,
        cust.full_name AS customer_name,
        cc.category,
        cc.severity,
        cc.status,
        cc.escalated,
        cc.assigned_to,
        rev.full_name AS assigned_to_name,
        DATE_FORMAT(cc.created_at, '%%Y-%%m-%%dT%%H:%%i:%%sZ') AS opened_at,
        DATE_FORMAT(cc.created_at, '%%Y-%%m-%%dT%%H:%%i:%%sZ') AS created_at,
        DATE_FORMAT(cc.updated_at, '%%Y-%%m-%%dT%%H:%%i:%%sZ') AS updated_at,
        cc.resolution_notes,
        cc.resolution_type,
        f.confidence,
        (f.confidence < %(threshold)s) AS needs_review,
        f.citation_label,
        f.source_url,
        f.page_number,
        f.quote_english,
        f.quote_original
    FROM compliance_case cc
    LEFT JOIN rm r ON cc.rm_id = r.rm_id
    LEFT JOIN customer cust ON cc.customer_id = cust.customer_id
    LEFT JOIN reviewer rev ON cc.assigned_to = rev.reviewer_id
    LEFT JOIN finding f ON cc.finding_id = f.finding_id
    WHERE {where_sql}
    ORDER BY cc.created_at DESC
    LIMIT %(limit)s OFFSET %(offset)s
    """

    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(count_sql, params)
            total = cur.fetchone()["total"]

            cur.execute(query_sql, params)
            items = cur.fetchall()

            for item in items:
                item["needs_review"] = bool(item.get("needs_review"))
                item["priority"] = item.get("severity", "MEDIUM")

    return {"total": total, "items": items}


def generate_detailed_recommended_action(
    category: str,
    severity: str,
    customer_name: Optional[str] = None,
    rm_name: Optional[str] = None,
    customer_risk_profile: Optional[str] = None,
    needs_review: bool = False
) -> str:
    cust = customer_name or "the client"
    rm = rm_name or "the Relationship Manager"
    risk = customer_risk_profile or "recorded risk profile"
    
    cat = (category or "").upper()
    if "PERFORMANCE" in cat or "CLAIM" in cat:
        return (
            f"1. Issue immediate written corrective disclosure to {cust} clarifying that past returns do not guarantee future performance and equity investments carry market volatility risks.\n"
            f"2. Mandate compliance retraining for {rm} regarding SEBI Mutual Fund advertisement codes and AMFI verbal disclosure mandates.\n"
            f"3. Place this account on 30-day branch surveillance and flag all subsequent market-linked product advisories for supervisory sign-off."
        )
    elif "SUITABILITY" in cat or "MISMATCH" in cat:
        return (
            f"1. Promptly halt order processing and re-validate {cust}'s suitability profile against the {risk} investment tier before finalizing any allocation.\n"
            f"2. Contact {cust} to deliver comprehensive statutory risk-o-meter disclosures and present suitable capital-protection alternatives without penalty.\n"
            f"3. Convene a supervisory compliance review with {rm} to audit recent sales pipelines for potential pressure-selling or profile mismatches."
        )
    elif "RISK" in cat or "DISCLOSURE" in cat:
        return (
            f"1. Transmit the official SEBI Scheme Information Document (SID) and Key Information Memorandum (KIM) with the scheme's Risk-o-meter to {cust} via registered email.\n"
            f"2. Enforce a mandatory 48-hour cooling-off period prior to transaction debits until formal written client risk acknowledgment is archived.\n"
            f"3. Conduct a branch audit on {rm}'s oral disclosure compliance checklist and inspect mandatory recorded call disclaimers."
        )
    elif "GUARANTEE" in cat or "RETURN" in cat:
        return (
            f"1. Dispatch an urgent formal retraction notice to {cust} explicitly disclaiming any implied or express return assurances on market-linked securities.\n"
            f"2. Ensure {cust} confirms understanding of NAV fluctuations, capital risk, and lack of return guarantees prior to proceeding.\n"
            f"3. Initiate a formal compliance inquiry with {rm} regarding statutory prohibitions on return assurances under SEBI regulations."
        )
    else:
        if needs_review:
            return (
                f"1. Escalate case file to Principal Compliance Officer for expedited manual review due to low model confidence threshold.\n"
                f"2. Contact {cust} to verify if any verbal product commitments or unrecorded disclosures were communicated during the consultation.\n"
                f"3. Hold transaction execution until formal branch supervisory concurrence and written sign-off are recorded in the audit ledger."
            )
        return (
            f"1. Enforce corrective client advisory for {cust} with verified statutory product risk disclosures and scheme documentation.\n"
            f"2. Require {rm} to submit a formal incident explanation report to the Compliance Desk within 48 business hours.\n"
            f"3. Log this incident in the quarterly compliance register for statutory reporting and branch audit tracking."
        )


def format_detailed_reasoning(case_row: Dict[str, Any]) -> str:
    """Extracts or synthesizes an authoritative 2-3 line forensic reasoning for the finding."""
    evidence_data = {}
    if case_row.get("evidence"):
        if isinstance(case_row["evidence"], dict):
            evidence_data = case_row["evidence"]
        elif isinstance(case_row["evidence"], str):
            try:
                evidence_data = json.loads(case_row["evidence"])
            except Exception:
                evidence_data = {}

    forensic_reasoning = (
        evidence_data.get("rationale")
        or (evidence_data.get("supporting", [None])[0] if isinstance(evidence_data.get("supporting"), list) and evidence_data.get("supporting") else None)
        or case_row.get("resolution_notes")
    )

    if not forensic_reasoning or len(str(forensic_reasoning).strip()) < 40:
        cust = case_row.get("customer_name") or "the client"
        rm = case_row.get("rm_name") or "the Relationship Manager"
        risk = case_row.get("customer_risk_profile") or "conservative"
        cat = (case_row.get("category") or "").upper()
        if "PERFORMANCE" in cat:
            forensic_reasoning = (
                f"During the sales consultation, {rm} highlighted strong historical fund performance without delivering mandatory statutory disclaimers.\n"
                f"Under SEBI and AMFI regulations, presenting past performance without clarifying that past returns do not indicate future results creates an unfounded expectation of safety.\n"
                f"Forensic surveillance identified this communication as non-compliant with advertising and verbal performance presentation standards."
            )
        elif "SUITABILITY" in cat:
            forensic_reasoning = (
                f"The consultation revealed {rm} actively advising a high-risk investment vehicle to {cust}, whose risk profile is classified as {risk}.\n"
                f"SEBI master circulars explicitly prohibit recommending high-volatility financial products without assessing customer investment experience and tolerance thresholds.\n"
                f"This sales advice constitutes an unmitigated suitability mismatch under statutory investor protection frameworks."
            )
        elif "DISCLOSURE" in cat:
            forensic_reasoning = (
                f"{rm} omitted mandatory scheme risk disclosures and downplayed market volatility when discussing the investment with {cust}.\n"
                f"Regulatory guidelines require proactive oral articulation of the Scheme Risk-o-meter, volatility factors, and capital loss potential during sales calls.\n"
                f"Failure to deliver these disclosures deprives the investor of essential statutory risk context prior to financial commitment."
            )
        elif "GUARANTEE" in cat:
            forensic_reasoning = (
                f"The spoken dialogue contains statements from {rm} assuring or strongly implying capital safety and positive return recovery over time.\n"
                f"SEBI regulations strictly forbid any direct or implied assurance of returns on market-linked securities.\n"
                f"This assurance compromises regulatory integrity and misleads {cust} into viewing equity risk as fixed-income security."
            )
        else:
            forensic_reasoning = (
                f"Forensic acoustic surveillance and statutory regulatory matching identified non-compliant sales conduct during the consultation.\n"
                f"The dialogue fails to satisfy SEBI compliance standards applicable to investor communication and product distribution.\n"
                f"Supervisory audit is required to ensure statutory disclosure obligations are fully restored."
            )
    return str(forensic_reasoning).strip()


def get_case_detail(case_id: str) -> Optional[Dict[str, Any]]:
    """
    Assembles the complete Evidence Chain for a compliance case:
    - Case & review status
    - Confirmed finding & verbatim quotes
    - Statutory citation, regulation clause, page number, source URL
    - Customer profile & product details
    - Staged candidate and investigation reasoning
    - RM historical violations
    - Full case activity log
    """
    threshold = get_current_confidence_threshold()

    case_sql = """
    SELECT 
        cc.*,
        r.full_name AS rm_name,
        r.branch AS rm_branch,
        cust.full_name AS customer_name,
        cust.risk_profile AS customer_risk_profile,
        cust.investment_experience AS customer_investment_experience,
        rev.full_name AS assigned_to_name,
        f.regulation_chunk_id,
        f.citation_label,
        f.source_url,
        f.page_number,
        f.confidence,
        f.category AS finding_category,
        f.severity AS finding_severity,
        f.timestamp_start,
        f.timestamp_end,
        f.quote_original,
        f.quote_english,
        f.evidence,
        f.model AS model_used,
        f.provider_used,
        reg.chunk_text AS regulation_clause_text,
        reg.document_name AS regulation_document_name,
        reg.clause AS regulation_clause
    FROM compliance_case cc
    LEFT JOIN rm r ON cc.rm_id = r.rm_id
    LEFT JOIN customer cust ON cc.customer_id = cust.customer_id
    LEFT JOIN reviewer rev ON cc.assigned_to = rev.reviewer_id
    LEFT JOIN finding f ON cc.finding_id = f.finding_id
    LEFT JOIN regulation_chunk_registry reg ON f.regulation_chunk_id = reg.chunk_id
    WHERE cc.case_id = %s
    """

    activity_sql = """
    SELECT 
        log_id,
        case_id,
        action,
        actor,
        details,
        DATE_FORMAT(timestamp, '%%Y-%%m-%%dT%%H:%%i:%%sZ') AS timestamp
    FROM case_activity_log
    WHERE case_id = %s
    ORDER BY timestamp ASC
    """

    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(case_sql, (case_id,))
            case_row = cur.fetchone()
            if not case_row:
                return None

            cur.execute(activity_sql, (case_id,))
            activity_log = cur.fetchall()

            call_sql = """
            SELECT id AS call_id, duration_s, duration_s AS duration_seconds, language, gcs_uri_archive, gcs_uri_incoming, date_time
            FROM `call`
            WHERE id = %s
            """
            cur.execute(call_sql, (case_row["call_id"],))
            call_row = cur.fetchone() or {}

            # Query real stage timings from pipeline_stage_timing
            timing_sql = """
            SELECT stage_name, duration_ms, start_time, end_time, status
            FROM pipeline_stage_timing
            WHERE call_id = %s
            ORDER BY id ASC
            """
            cur.execute(timing_sql, (case_row["call_id"],))
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

            run_sql = """
            SELECT total_duration_ms, start_time, end_time
            FROM pipeline_run
            WHERE call_id = %s AND status = 'COMPLETED'
            ORDER BY start_time DESC
            LIMIT 1
            """
            cur.execute(run_sql, (case_row["call_id"],))
            run_row = cur.fetchone()
            if run_row and run_row.get("total_duration_ms"):
                call_row["e2e_duration_s"] = round(run_row["total_duration_ms"] / 1000.0, 1)
            elif ingest_sec is not None and detect_sec is not None and invest_sec is not None:
                call_row["e2e_duration_s"] = round(ingest_sec + detect_sec + invest_sec + (archive_sec or 0), 1)
            else:
                call_row["e2e_duration_s"] = None

            # Query synchronized transcript segments
            segments_sql = """
            SELECT 
                segment_id,
                call_id,
                idx,
                speaker_label,
                role,
                role AS speaker,
                start_ms,
                end_ms,
                ROUND(start_ms / 1000.0, 2) AS start_time,
                ROUND(end_ms / 1000.0, 2) AS end_time,
                text_original,
                text_english,
                COALESCE(text_english, text_original) AS text,
                is_violation
            FROM transcript_segment
            WHERE call_id = %s
            ORDER BY idx ASC
            """
            cur.execute(segments_sql, (case_row["call_id"],))
            segments = cur.fetchall() or []

            for seg in segments:
                s_secs = int(seg.get("start_time") or 0)
                m, s = divmod(s_secs, 60)
                seg["timestamp_display"] = f"{m:02d}:{s:02d}"

            call_row["transcript"] = segments
            call_row["transcript_segments"] = segments
            case_row["transcript_segments"] = segments

            # Query sibling cases for this call
            sibling_cases_sql = """
            SELECT case_id, finding_id, category, severity, status
            FROM compliance_case
            WHERE call_id = %s
            ORDER BY created_at ASC
            """
            cur.execute(sibling_cases_sql, (case_row["call_id"],))
            call_row["cases"] = cur.fetchall() or []

    # Format Evidence Chain response
    confidence = float(case_row.get("confidence") or 0.0)
    needs_review = confidence < threshold

    # Format timestamp display
    start_s = case_row.get("timestamp_start") or 0
    end_s = case_row.get("timestamp_end") or 0
    m1, s1 = divmod(start_s, 60)
    m2, s2 = divmod(end_s, 60)
    timestamp_display = f"{m1:02d}:{s1:02d} - {m2:02d}:{s2:02d}"

    case_row["needs_review"] = needs_review
    case_row["timestamp_display"] = timestamp_display
    case_row["activity_log"] = activity_log
    case_row["confidence_threshold_applied"] = threshold
    case_row["call"] = call_row

    # Nested case object for frontend contract
    case_row["case"] = {
        "case_id": case_row.get("case_id"),
        "finding_id": case_row.get("finding_id"),
        "call_id": case_row.get("call_id"),
        "rm_id": case_row.get("rm_id"),
        "rm_name": case_row.get("rm_name"),
        "rm_branch": case_row.get("rm_branch"),
        "customer_id": case_row.get("customer_id"),
        "customer_name": case_row.get("customer_name"),
        "category": case_row.get("category"),
        "severity": case_row.get("severity"),
        "status": case_row.get("status"),
        "resolution_type": case_row.get("resolution_type"),
        "escalated": bool(case_row.get("escalated")),
        "assigned_to": case_row.get("assigned_to"),
        "assignee_name": case_row.get("assigned_to_name"),
        "resolution_notes": case_row.get("resolution_notes"),
        "created_at": case_row["created_at"].isoformat() if hasattr(case_row.get("created_at"), "isoformat") else str(case_row.get("created_at") or ""),
        "updated_at": case_row["updated_at"].isoformat() if hasattr(case_row.get("updated_at"), "isoformat") else str(case_row.get("updated_at") or ""),
    }

    forensic_reasoning = format_detailed_reasoning(case_row)
    detailed_action = generate_detailed_recommended_action(
        category=case_row.get("category") or "",
        severity=case_row.get("severity") or "MEDIUM",
        customer_name=case_row.get("customer_name"),
        rm_name=case_row.get("rm_name"),
        customer_risk_profile=case_row.get("customer_risk_profile"),
        needs_review=needs_review
    )

    # Structure nested finding object for frontend compatibility
    case_row["finding"] = {
        "finding_id": case_row.get("finding_id"),
        "call_id": case_row.get("call_id"),
        "category": case_row.get("category"),
        "severity": case_row.get("severity"),
        "confidence": confidence,
        "regulation_chunk_id": case_row.get("regulation_chunk_id"),
        "regulation_citation_label": case_row.get("citation_label"),
        "regulation_source_url": case_row.get("source_url"),
        "regulation_page_number": case_row.get("page_number"),
        "regulation_clause_text": case_row.get("regulation_clause_text"),
        "quote_original": case_row.get("quote_original"),
        "quote_english": case_row.get("quote_english"),
        "transcript_evidence": case_row.get("quote_english") or case_row.get("quote_original"),
        "timestamp_start": start_s,
        "timestamp_end": end_s,
        "timestamp_display": timestamp_display,
        "customer_risk_profile": case_row.get("customer_risk_profile"),
        "reasoning": forensic_reasoning,
        "recommended_action": detailed_action
    }

    return case_row


def update_case_status(case_id: str, reviewer_id: str, action: str, notes: Optional[str] = None) -> Dict[str, Any]:
    """
    Executes 'mark_reviewed' or 'dismiss' atomically.
    Raises CaseAlreadyResolvedError (409) if the case is not OPEN.
    """
    action_clean = action.lower()
    if action_clean not in ("mark_reviewed", "dismiss"):
        raise ValueError(f"Invalid case status action '{action}'. Must be 'mark_reviewed' or 'dismiss'.")

    res_type = "CONFIRMED_ACTION_TAKEN" if action_clean == "mark_reviewed" else "DISMISSED_FALSE_POSITIVE"

    check_sql = "SELECT case_id, status FROM compliance_case WHERE case_id = %s FOR UPDATE"
    update_sql = """
    UPDATE compliance_case
    SET status = 'RESOLVED',
        resolution_type = %s,
        resolution_notes = %s,
        updated_at = CURRENT_TIMESTAMP
    WHERE case_id = %s
    """
    log_sql = """
    INSERT INTO case_activity_log (case_id, action, actor, details)
    VALUES (%s, 'STATUS_CHANGE', %s, %s)
    """

    with db_manager.transaction() as cur:
        cur.execute(check_sql, (case_id,))
        row = cur.fetchone()
        if not row:
            raise CaseNotFoundError(case_id)
        if row["status"] != "OPEN":
            raise CaseAlreadyResolvedError(case_id)

        detail_text = f"Action: {action_clean}. Notes: {notes or 'No notes provided'}"
        cur.execute(update_sql, (res_type, notes, case_id))
        cur.execute(log_sql, (case_id, reviewer_id, detail_text))

    return get_case_detail(case_id)


def escalate_case(case_id: str, reviewer_id: str, notes: Optional[str] = None) -> Dict[str, Any]:
    """
    Escalates case to the Compliance Committee.
    Raises CaseAlreadyEscalatedError (409) if already escalated.
    """
    check_sql = "SELECT case_id, status, escalated FROM compliance_case WHERE case_id = %s FOR UPDATE"
    update_sql = """
    UPDATE compliance_case
    SET escalated = TRUE,
        resolution_notes = COALESCE(CONCAT(COALESCE(resolution_notes, ''), '\n[Escalation]: ', %s), %s),
        updated_at = CURRENT_TIMESTAMP
    WHERE case_id = %s
    """
    log_sql = """
    INSERT INTO case_activity_log (case_id, action, actor, details)
    VALUES (%s, 'ESCALATED', %s, %s)
    """

    with db_manager.transaction() as cur:
        cur.execute(check_sql, (case_id,))
        row = cur.fetchone()
        if not row:
            raise CaseNotFoundError(case_id)
        if row.get("escalated"):
            raise CaseAlreadyEscalatedError(case_id)

        detail_text = f"Escalated to committee by {reviewer_id}. Notes: {notes or 'No notes'}"
        cur.execute(update_sql, (notes or "", notes or "", case_id))
        cur.execute(log_sql, (case_id, reviewer_id, detail_text))

    return get_case_detail(case_id)


def assign_case(case_id: str, reviewer_id: str, assignee_reviewer_id: str) -> Dict[str, Any]:
    """
    Assigns or re-assigns case to a reviewer. Idempotent.
    """
    check_rev_sql = "SELECT reviewer_id, full_name FROM reviewer WHERE reviewer_id = %s"
    check_case_sql = "SELECT case_id, assigned_to FROM compliance_case WHERE case_id = %s FOR UPDATE"
    update_sql = """
    UPDATE compliance_case
    SET assigned_to = %s,
        updated_at = CURRENT_TIMESTAMP
    WHERE case_id = %s
    """
    log_sql = """
    INSERT INTO case_activity_log (case_id, action, actor, details)
    VALUES (%s, 'ASSIGNED', %s, %s)
    """

    with db_manager.transaction() as cur:
        cur.execute(check_rev_sql, (assignee_reviewer_id,))
        rev = cur.fetchone()
        if not rev:
            raise ReviewerNotFoundError(assignee_reviewer_id)

        cur.execute(check_case_sql, (case_id,))
        case_row = cur.fetchone()
        if not case_row:
            raise CaseNotFoundError(case_id)

        detail_text = f"Assigned to {rev['full_name']} ({assignee_reviewer_id}) by {reviewer_id}"
        cur.execute(update_sql, (assignee_reviewer_id, case_id))
        cur.execute(log_sql, (case_id, reviewer_id, detail_text))

    return get_case_detail(case_id)


def add_case_note(case_id: str, reviewer_id: str, notes: str) -> Dict[str, Any]:
    """
    Appends an audit note to the case activity log. Always allowed for open/resolved cases.
    """
    check_case_sql = "SELECT case_id FROM compliance_case WHERE case_id = %s"
    log_sql = """
    INSERT INTO case_activity_log (case_id, action, actor, details)
    VALUES (%s, 'NOTE_ADDED', %s, %s)
    """

    with db_manager.transaction() as cur:
        cur.execute(check_case_sql, (case_id,))
        if not cur.fetchone():
            raise CaseNotFoundError(case_id)
        cur.execute(log_sql, (case_id, reviewer_id, notes))

    return get_case_detail(case_id)
