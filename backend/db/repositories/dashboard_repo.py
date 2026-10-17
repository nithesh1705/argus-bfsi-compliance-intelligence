"""
ARGUS — Dashboard Repository (backend/db/repositories/dashboard_repo.py)

Generates aggregated surveillance metrics, category breakdowns, and stage-wise
pipeline latency summaries for the executive compliance dashboard.
"""

import statistics
import logging
from typing import Dict, Any, List

from backend.adapters.database import db_manager
from backend.db.repositories.cases_repo import list_cases

logger = logging.getLogger("argus.db.dashboard")


def get_pipeline_latency_summary() -> Dict[str, Any]:
    """
    Computes latency statistics (mean, median, min, max) across pipeline stages
    and end-to-end from pipeline_stage_timing and pipeline_run tables.
    """
    stage_sql = """
    SELECT stage_name, duration_ms
    FROM pipeline_stage_timing
    ORDER BY stage_name
    """
    run_sql = """
    SELECT total_duration_ms
    FROM pipeline_run
    WHERE status = 'COMPLETED' AND total_duration_ms > 0
    """

    stages_data: Dict[str, List[int]] = {}
    end_to_end_data: List[int] = []

    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(stage_sql)
            for row in cur.fetchall():
                st = row["stage_name"]
                stages_data.setdefault(st, []).append(row["duration_ms"])

            cur.execute(run_sql)
            for row in cur.fetchall():
                end_to_end_data.append(row["total_duration_ms"])

    def calc_stats(vals: List[int]) -> Dict[str, float]:
        if not vals:
            return {"mean": 0.0, "median": 0.0, "min": 0.0, "max": 0.0, "count": 0}
        return {
            "mean": round(statistics.mean(vals), 1),
            "median": round(statistics.median(vals), 1),
            "min": min(vals),
            "max": max(vals),
            "count": len(vals),
        }

    stages_summary = {st: calc_stats(v) for st, v in stages_data.items()}
    end_to_end_summary = calc_stats(end_to_end_data)

    return {
        "end_to_end": end_to_end_summary,
        "stages": stages_summary,
    }


def get_dashboard_summary() -> Dict[str, Any]:
    """
    Returns high-density dashboard KPIs, severity breakdown, top violators,
    recent cases, and real pipeline latency.
    """
    calls_sql = "SELECT COUNT(*) AS total_calls FROM `call`"
    
    findings_sql = """
    SELECT 
        COUNT(*) AS total_findings,
        SUM(CASE WHEN severity = 'HIGH' THEN 1 ELSE 0 END) AS high_count,
        SUM(CASE WHEN severity = 'MEDIUM' THEN 1 ELSE 0 END) AS medium_count,
        SUM(CASE WHEN severity = 'LOW' THEN 1 ELSE 0 END) AS low_count
    FROM finding
    """

    categories_sql = """
    SELECT category, COUNT(*) AS count
    FROM finding
    GROUP BY category
    ORDER BY count DESC
    """

    cases_status_sql = """
    SELECT 
        SUM(CASE WHEN status = 'OPEN' THEN 1 ELSE 0 END) AS open_cases,
        SUM(CASE WHEN status = 'RESOLVED' THEN 1 ELSE 0 END) AS resolved_cases,
        SUM(CASE WHEN escalated = TRUE THEN 1 ELSE 0 END) AS escalated_cases
    FROM compliance_case
    """

    top_rms_sql = """
    SELECT 
        r.rm_id,
        r.full_name AS rm_name,
        r.branch,
        COUNT(f.finding_id) AS violations_count,
        SUM(CASE WHEN f.severity = 'HIGH' THEN 1 ELSE 0 END) AS high_count
    FROM rm r
    JOIN `call` c ON r.rm_id = c.rm_id
    JOIN finding f ON c.id = f.call_id
    GROUP BY r.rm_id, r.full_name, r.branch
    ORDER BY violations_count DESC, high_count DESC
    LIMIT 5
    """

    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(calls_sql)
            total_calls = cur.fetchone()["total_calls"]

            cur.execute(findings_sql)
            find_row = cur.fetchone()
            total_findings = find_row["total_findings"] or 0
            severity_counts = {
                "HIGH": int(find_row["high_count"] or 0),
                "MEDIUM": int(find_row["medium_count"] or 0),
                "LOW": int(find_row["low_count"] or 0),
            }

            cur.execute(categories_sql)
            category_counts = {r["category"]: r["count"] for r in cur.fetchall()}

            cur.execute(cases_status_sql)
            case_row = cur.fetchone()
            case_status_counts = {
                "OPEN": int(case_row["open_cases"] or 0),
                "RESOLVED": int(case_row["resolved_cases"] or 0),
                "ESCALATED": int(case_row["escalated_cases"] or 0),
            }

            cur.execute(top_rms_sql)
            top_rms = cur.fetchall()

    recent_cases_res = list_cases(limit=10, offset=0)
    latency_summary = get_pipeline_latency_summary()

    total_cases = case_status_counts["OPEN"] + case_status_counts["RESOLVED"]

    kpis = {
        "total_calls": total_calls,
        "total_findings": total_findings,
        "total_cases": total_cases,
        "open_cases": case_status_counts["OPEN"],
        "resolved_cases": case_status_counts["RESOLVED"],
        "escalated_cases": case_status_counts["ESCALATED"],
        "confidence_threshold": 0.75,
    }

    rm_violation_trend = [
        {
            "rm_id": r["rm_id"],
            "rm_name": r["rm_name"],
            "branch": r.get("branch", ""),
            "violation_count": r.get("violations_count", 0),
        }
        for r in top_rms
    ]

    category_breakdown = [
        {"category": cat, "count": cnt}
        for cat, cnt in category_counts.items()
    ]

    return {
        # Structured contract expected by frontend
        "kpis": kpis,
        "findings_by_severity": severity_counts,
        "rm_violation_trend": rm_violation_trend,
        "category_breakdown": category_breakdown,
        "recent_cases": recent_cases_res["items"],
        "pipeline_latency": latency_summary,
        # Backward-compatible flat fields
        "total_calls": total_calls,
        "total_calls_monitored": total_calls,
        "total_findings": total_findings,
        "total_violations_flagged": total_findings,
        "severity_counts": severity_counts,
        "category_counts": category_counts,
        "case_status_counts": case_status_counts,
        "top_violating_rms": top_rms,
    }
