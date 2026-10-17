"""
ARGUS — RM Report Service (backend/reports/rm_report_service.py)
Prepares data for RM Compliance Reports and manages audit logging & idempotency.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import uuid

from backend.adapters.database import db_manager
from backend.db.repositories.rm_repo import get_rm_analytics
from backend.db.repositories.cases_repo import format_detailed_reasoning, generate_detailed_recommended_action

logger = logging.getLogger("argus.reports.rm")

# In-memory idempotency cache (or DB-backed)
_idempotency_cache: Dict[str, Dict[str, Any]] = {}


def check_idempotency(request_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """Check if a report send request was already processed."""
    if not request_id:
        return None
    return _idempotency_cache.get(request_id)


def record_report_audit(request_id: Optional[str], response_data: Dict[str, Any]) -> None:
    """Record the sent report audit log."""
    if request_id:
        _idempotency_cache[request_id] = response_data


def get_rm_report_data(rm_id: str, app_url: str = "") -> Optional[Dict[str, Any]]:
    """
    Assembles comprehensive report data for HTML/text rendering.
    """
    analytics = get_rm_analytics(rm_id)
    if not analytics:
        return None

    report_id = f"REP-{rm_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    generated_at = datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC")

    # Fetch detailed findings for report cards
    findings_sql = """
    SELECT 
        f.finding_id,
        f.call_id,
        f.category,
        f.severity,
        ROUND(f.confidence * 100) AS confidence_pct,
        f.quote_english AS transcript_evidence,
        f.citation_label AS regulation_citation_label,
        f.source_url AS regulation_source_url,
        f.timestamp_start,
        f.timestamp_end,
        f.evidence,
        cc.case_id,
        cc.status AS case_status,
        cust.full_name AS customer_name,
        cust.risk_profile AS customer_risk_profile,
        p.risk_class AS product_risk_class,
        reg.document_name AS regulation_document_name,
        reg.chunk_text AS regulation_clause_text
    FROM finding f
    JOIN `call` c ON f.call_id = c.id
    LEFT JOIN compliance_case cc ON f.finding_id = cc.finding_id
    LEFT JOIN customer cust ON c.customer_id = cust.customer_id
    LEFT JOIN product p ON c.product_id = p.product_id
    LEFT JOIN regulation_chunk_registry reg ON f.regulation_chunk_id = reg.chunk_id
    WHERE c.rm_id = %s
    ORDER BY f.severity = 'HIGH' DESC, f.finding_id ASC
    """

    # Fetch calls for table
    calls_sql = """
    SELECT 
        c.id AS call_id,
        c.customer_id,
        cust.full_name AS customer_name,
        DATE_FORMAT(c.date_time, '%%d %%b %%Y %%H:%%i') AS date_time,
        c.language,
        CONCAT(FLOOR(COALESCE(c.duration_s, 0) / 60), 'm ', FLOOR(MOD(COALESCE(c.duration_s, 0), 60)), 's') AS duration_formatted,
        CASE WHEN COUNT(f.finding_id) > 0 THEN 'VIOLATION' ELSE 'CLEAN' END AS violation_status
    FROM `call` c
    LEFT JOIN customer cust ON c.customer_id = cust.customer_id
    LEFT JOIN finding f ON c.id = f.call_id
    WHERE c.rm_id = %s
    GROUP BY c.id, c.customer_id, cust.full_name, c.date_time, c.language, c.duration_s
    ORDER BY c.date_time DESC
    """

    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(findings_sql, (rm_id,))
            findings = cur.fetchall()

            cur.execute(calls_sql, (rm_id,))
            calls = cur.fetchall()

    for f in findings:
        start_s = int(f.get("timestamp_start") or 0)
        end_s = int(f.get("timestamp_end") or 0)
        f["timestamp_interval"] = f"{start_s // 60:02d}:{start_s % 60:02d} - {end_s // 60:02d}:{end_s % 60:02d}"
        
        f["reasoning"] = format_detailed_reasoning({
            "category": f.get("category"),
            "customer_name": f.get("customer_name"),
            "rm_name": analytics["rm"]["full_name"],
            "customer_risk_profile": f.get("customer_risk_profile"),
            "product_risk_class": f.get("product_risk_class"),
            "evidence": f.get("evidence"),
        })
        f["recommended_action"] = generate_detailed_recommended_action(
            category=f.get("category") or "",
            severity=f.get("severity") or "HIGH",
            customer_name=f.get("customer_name"),
            rm_name=analytics["rm"]["full_name"],
            customer_risk_profile=f.get("customer_risk_profile"),
        )

    has_repeat = analytics.get("has_repeat_violations", False)
    total_violations = analytics.get("total_cases", len(findings))

    if has_repeat:
        status_type = "REPEAT_VIOLATIONS"
        headline = "Systemic Pattern: Repeat Statutory Violations Flagged"
        summary = f"Relationship Manager has accumulated {total_violations} confirmed compliance cases with recurring statutory infractions."
    elif total_violations > 0:
        status_type = "REVIEW_REQUIRED"
        headline = "Compliance Review Required"
        summary = f"Relationship Manager has registered {total_violations} compliance cases requiring managerial oversight."
    elif analytics.get("total_calls", 0) == 0:
        status_type = "NO_CALLS"
        headline = "No Advisory Calls Monitored"
        summary = "No indexed advisory audio calls have been recorded for surveillance."
    else:
        status_type = "CLEAN"
        headline = "Surveillance Clear: Zero Confirmed Infractions"
        summary = "All monitored advisory communications conform with SEBI and AMFI regulatory standards."

    calls_with_findings = sum(1 for c in calls if c.get("violation_status") == "VIOLATION")
    clean_calls = sum(1 for c in calls if c.get("violation_status") == "CLEAN")
    total_calls = len(calls) if calls else analytics.get("total_calls", 0)
    high_count = analytics.get("high_severity_count", 0)
    med_count = analytics.get("medium_severity_count", 0)
    low_count = analytics.get("low_severity_count", 0)
    open_cases = analytics.get("open_cases", 0)
    risk_score = analytics.get("risk_score", 0)

    return {
        "report_id": report_id,
        "generated_at": generated_at,
        "app_url": app_url,
        "rm": analytics["rm"],
        "metrics": {
            "risk_score": risk_score,
            "total_calls": total_calls,
            "clean_calls": clean_calls,
            "calls_with_findings": calls_with_findings,
            "total_violations": total_violations,
            "total_cases": total_violations,
            "open_cases": open_cases,
            "high_severity_count": high_count,
            "medium_severity_count": med_count,
            "low_severity_count": low_count,
            "reporting_period": "Q1 2026 (Live Surveillance)",
        },
        "status_evaluation": {
            "status_type": status_type,
            "headline": headline,
            "summary": summary,
        },
        "calls": calls,
        "findings": findings,
        "cases": analytics.get("recent_cases", []),
    }
