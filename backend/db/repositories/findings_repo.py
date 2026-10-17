"""
ARGUS — Findings Repository (backend/db/repositories/findings_repo.py)

Manages persistence of confirmed regulatory findings and handles the
single-transaction atomic commit:
finding + compliance_case + call.has_violation update + case_activity_log.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from backend.adapters.database import db_manager

logger = logging.getLogger("argus.db.findings")


def commit_confirmed_finding(finding_data: Dict[str, Any]) -> str:
    """
    Transactional Upgrade:
    In one single MySQL transaction:
    1. Inserts the finding row
    2. Inserts or links the compliance_case row
    3. Updates call.has_violation = TRUE, severity, and increments finding_count
    4. Inserts the INITIAL case_activity_log entry
    """
    finding_id = finding_data["finding_id"]
    call_id = finding_data["call_id"]
    case_id = finding_data.get("case_id", f"CASE_{finding_id.replace('FND-', '')}")

    insert_finding_sql = """
    INSERT INTO finding (
        finding_id, call_id, investigation_id, regulation_chunk_id, citation_label,
        source_url, page_number, severity, confidence, category, timestamp_start,
        timestamp_end, quote_original, quote_english, evidence, provider_used, model
    ) VALUES (
        %(finding_id)s, %(call_id)s, %(investigation_id)s, %(regulation_chunk_id)s, %(citation_label)s,
        %(source_url)s, %(page_number)s, %(severity)s, %(confidence)s, %(category)s, %(timestamp_start)s,
        %(timestamp_end)s, %(quote_original)s, %(quote_english)s, %(evidence)s, %(provider_used)s, %(model)s
    ) ON DUPLICATE KEY UPDATE
        confidence = VALUES(confidence),
        severity = VALUES(severity),
        evidence = VALUES(evidence)
    """

    insert_case_sql = """
    INSERT INTO compliance_case (
        case_id, finding_id, call_id, rm_id, customer_id, category, severity, status, escalated
    ) VALUES (
        %(case_id)s, %(finding_id)s, %(call_id)s, %(rm_id)s, %(customer_id)s, %(category)s, %(severity)s, 'OPEN', FALSE
    ) ON DUPLICATE KEY UPDATE
        severity = VALUES(severity),
        category = VALUES(category)
    """

    update_call_sql = """
    UPDATE `call`
    SET has_violation = TRUE,
        finding_count = finding_count + 1,
        severity = CASE 
            WHEN %(severity)s = 'HIGH' THEN 'HIGH'
            WHEN severity = 'HIGH' THEN 'HIGH'
            WHEN %(severity)s = 'MEDIUM' THEN 'MEDIUM'
            ELSE COALESCE(severity, %(severity)s)
        END,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = %(call_id)s
    """

    insert_log_sql = """
    INSERT INTO case_activity_log (case_id, action, actor, details)
    VALUES (%(case_id)s, 'CREATED', 'SYSTEM', %(details)s)
    """

    # Prepare evidence json string if dict
    evidence_val = finding_data.get("evidence", {})
    if isinstance(evidence_val, dict) or isinstance(evidence_val, list):
        evidence_json = json.dumps(evidence_val)
    else:
        evidence_json = str(evidence_val)

    # Get RM and Customer from call
    with db_manager.transaction() as cur:
        cur.execute("SELECT rm_id, customer_id FROM `call` WHERE id = %s", (call_id,))
        call_info = cur.fetchone()
        rm_id = call_info["rm_id"] if call_info else "RM001"
        customer_id = call_info["customer_id"] if call_info else "CUST001"

        f_params = {
            "finding_id": finding_id,
            "call_id": call_id,
            "investigation_id": finding_data.get("investigation_id", f"INV-{finding_id}"),
            "regulation_chunk_id": finding_data.get("regulation_chunk_id", ""),
            "citation_label": finding_data.get("citation_label", ""),
            "source_url": finding_data.get("source_url", ""),
            "page_number": finding_data.get("page_number", 1) or 1,
            "severity": finding_data.get("severity", "MEDIUM"),
            "confidence": finding_data.get("confidence", 0.9),
            "category": finding_data.get("category", "SUITABILITY_MISMATCH"),
            "timestamp_start": finding_data.get("timestamp_start", 0),
            "timestamp_end": finding_data.get("timestamp_end", 0),
            "quote_original": finding_data.get("quote_original", ""),
            "quote_english": finding_data.get("quote_english", ""),
            "evidence": evidence_json,
            "provider_used": finding_data.get("provider_used", "mock"),
            "model": finding_data.get("model", "gemini-3.5-flash"),
        }
        cur.execute(insert_finding_sql, f_params)

        c_params = {
            "case_id": case_id,
            "finding_id": finding_id,
            "call_id": call_id,
            "rm_id": rm_id,
            "customer_id": customer_id,
            "category": finding_data.get("category", "SUITABILITY_MISMATCH"),
            "severity": finding_data.get("severity", "MEDIUM"),
        }
        cur.execute(insert_case_sql, c_params)

        cur.execute(update_call_sql, {"call_id": call_id, "severity": finding_data.get("severity", "MEDIUM")})

        log_params = {
            "case_id": case_id,
            "details": f"Automated compliance finding confirmed by Investigation Agent. Severity: {finding_data.get('severity')}. Citation: {finding_data.get('citation_label')}."
        }
        cur.execute(insert_log_sql, log_params)

    return finding_id


def list_findings(call_id: Optional[str] = None, severity: Optional[str] = None) -> List[Dict[str, Any]]:
    """Lists findings with optional filtering."""
    where_sql = "1=1"
    params = []

    if call_id:
        where_sql += " AND call_id = %s"
        params.append(call_id)
    if severity:
        where_sql += " AND severity = %s"
        params.append(severity.upper())

    sql = f"""
    SELECT 
        finding_id,
        call_id,
        regulation_chunk_id,
        citation_label,
        source_url,
        page_number,
        severity,
        confidence,
        category,
        timestamp_start,
        timestamp_end,
        quote_original,
        quote_english,
        provider_used,
        model,
        DATE_FORMAT(created_at, '%%Y-%%m-%%dT%%H:%%i:%%sZ') AS created_at
    FROM finding
    WHERE {where_sql}
    ORDER BY created_at DESC
    """
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(params))
            return cur.fetchall()
