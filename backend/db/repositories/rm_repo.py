"""
ARGUS — RM Analytics & History Repository (backend/db/repositories/rm_repo.py)

Calculates Relationship Manager violation analytics, risk scores, and prior
violation histories directly via SQL aggregations over findings and calls,
replacing legacy Elasticsearch aggregations.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from backend.adapters.database import db_manager

logger = logging.getLogger("argus.db.rm")


def get_rm_list_with_stats() -> List[Dict[str, Any]]:
    """
    Returns the RM roster enriched with aggregate surveillance metrics:
    - total_calls
    - total_violations (confirmed findings)
    - high_severity_count, medium_severity_count, low_severity_count
    - repeat_violation_flag
    - computed risk score (0 - 100)
    """
    sql = """
    SELECT 
        r.rm_id,
        r.full_name AS name,
        r.branch,
        r.active,
        COALESCE(call_stats.total_calls, 0) AS total_calls,
        COALESCE(find_stats.total_violations, 0) AS total_violations,
        COALESCE(find_stats.high_count, 0) AS high_severity_count,
        COALESCE(find_stats.medium_count, 0) AS medium_severity_count,
        COALESCE(find_stats.low_count, 0) AS low_severity_count,
        CASE WHEN COALESCE(find_stats.total_violations, 0) > 1 THEN TRUE ELSE FALSE END AS repeat_violation_flag
    FROM rm r
    LEFT JOIN (
        SELECT rm_id, COUNT(*) AS total_calls
        FROM `call`
        GROUP BY rm_id
    ) call_stats ON r.rm_id = call_stats.rm_id
    LEFT JOIN (
        SELECT 
            c.rm_id,
            COUNT(f.finding_id) AS total_violations,
            SUM(CASE WHEN f.severity = 'HIGH' THEN 1 ELSE 0 END) AS high_count,
            SUM(CASE WHEN f.severity = 'MEDIUM' THEN 1 ELSE 0 END) AS medium_count,
            SUM(CASE WHEN f.severity = 'LOW' THEN 1 ELSE 0 END) AS low_count
        FROM finding f
        JOIN `call` c ON f.call_id = c.id
        GROUP BY c.rm_id
    ) find_stats ON r.rm_id = find_stats.rm_id
    ORDER BY total_violations DESC, high_severity_count DESC, r.rm_id ASC
    """

    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()

    for row in rows:
        # Risk score calculation: High * 30 + Medium * 15 + Low * 5, capped at 100
        high = int(row.get("high_severity_count") or 0)
        med = int(row.get("medium_severity_count") or 0)
        low = int(row.get("low_severity_count") or 0)
        raw_score = (high * 35) + (med * 15) + (low * 5)
        row["risk_score"] = min(100, max(0, raw_score))
        row["region"] = row.get("branch", "West")
        row["manager_name"] = "Branch Compliance Supervisor"

    return rows


def get_rm_analytics(rm_id: str) -> Optional[Dict[str, Any]]:
    """
    Returns the comprehensive Relationship Manager surveillance dossier:
    - Master record (full_name, branch, email, joined_date, active)
    - Call counts
    - Severity distribution (HIGH, MEDIUM, LOW)
    - Regulatory category breakdown and repeat violation tags
    - Compliance case counts (open, resolved, escalated)
    - Recent associated incident cases
    - Historical surveillance trend
    """
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            # RM Master Profile
            cur.execute(
                "SELECT rm_id, full_name, branch, joined_date, active FROM rm WHERE rm_id = %s",
                (rm_id,)
            )
            rm_row = cur.fetchone()
            if not rm_row:
                return None

            # Calls Monitored
            cur.execute("SELECT COUNT(*) AS total_calls FROM `call` WHERE rm_id = %s", (rm_id,))
            call_res = cur.fetchone()
            total_calls = call_res["total_calls"] if call_res else 0

            # Findings Severity Breakdown
            cur.execute("""
                SELECT f.severity, COUNT(*) AS count
                FROM finding f
                JOIN `call` c ON f.call_id = c.id
                WHERE c.rm_id = %s
                GROUP BY f.severity
            """, (rm_id,))
            sev_rows = cur.fetchall()
            sev_map = {r["severity"]: r["count"] for r in sev_rows}
            severity_breakdown = [
                {"severity": "HIGH", "count": int(sev_map.get("HIGH", 0))},
                {"severity": "MEDIUM", "count": int(sev_map.get("MEDIUM", 0))},
                {"severity": "LOW", "count": int(sev_map.get("LOW", 0))},
            ]

            # Category Breakdown
            cur.execute("""
                SELECT f.category, COUNT(*) AS count
                FROM finding f
                JOIN `call` c ON f.call_id = c.id
                WHERE c.rm_id = %s
                GROUP BY f.category
                ORDER BY count DESC
            """, (rm_id,))
            cat_rows = cur.fetchall()
            repeat_categories = [r for r in cat_rows if r["count"] > 1]

            # Compliance Case Status Aggregations
            cur.execute("""
                SELECT status, escalated, COUNT(*) AS count
                FROM compliance_case
                WHERE rm_id = %s
                GROUP BY status, escalated
            """, (rm_id,))
            case_stat_rows = cur.fetchall()
            total_cases = sum(r["count"] for r in case_stat_rows)
            open_cases = sum(r["count"] for r in case_stat_rows if (r["status"] or "").upper() == "OPEN")
            resolved_cases = sum(r["count"] for r in case_stat_rows if (r["status"] or "").upper() == "RESOLVED")
            escalated_cases = sum(
                r["count"] for r in case_stat_rows 
                if r.get("escalated") or (r["status"] or "").upper() == "ESCALATED"
            )

            # Recent Associated Cases
            cur.execute("""
                SELECT 
                    case_id,
                    customer_id,
                    category,
                    severity,
                    status,
                    DATE_FORMAT(created_at, '%%%%Y-%%%%m-%%%%dT%%%%H:%%%%i:%%%%sZ') AS created_at
                FROM compliance_case
                WHERE rm_id = %s
                ORDER BY created_at DESC
                LIMIT 25
            """, (rm_id,))
            recent_cases = cur.fetchall()

            # Surveillance Monthly Trend
            cur.execute("""
                SELECT 
                    DATE_FORMAT(c.date_time, '%%b %%Y') AS month,
                    COUNT(DISTINCT c.id) AS calls,
                    COUNT(DISTINCT f.finding_id) AS violations
                FROM `call` c
                LEFT JOIN finding f ON c.id = f.call_id
                WHERE c.rm_id = %s AND c.date_time IS NOT NULL
                GROUP BY DATE_FORMAT(c.date_time, '%%b %%Y'), YEAR(c.date_time), MONTH(c.date_time)
                ORDER BY YEAR(c.date_time) ASC, MONTH(c.date_time) ASC
            """, (rm_id,))
            trend_rows = cur.fetchall()

    high_count = sev_map.get("HIGH", 0)
    med_count = sev_map.get("MEDIUM", 0)
    low_count = sev_map.get("LOW", 0)
    has_repeat_violations = len(repeat_categories) > 0 or total_cases > 1
    risk_score = min(
        100,
        (high_count * 30) + (med_count * 15) + (low_count * 5) + (25 if has_repeat_violations else 0)
    )

    branch = rm_row.get("branch") or "Mumbai Branch"
    region = (
        "West Region" if ("Mumbai" in branch or "Pune" in branch)
        else "South Region" if "Bengaluru" in branch
        else "North Region"
    )
    email = f"{rm_row['full_name'].lower().replace(' ', '.')}@argus.com"

    return {
        # Structured nested object expected by RMDetail.tsx
        "rm": {
            "rm_id": rm_row["rm_id"],
            "full_name": rm_row["full_name"],
            "branch": rm_row["branch"],
            "email": email,
            "joined_date": str(rm_row.get("joined_date") or ""),
            "active": bool(rm_row.get("active", True)),
        },
        "total_calls": total_calls,
        "total_cases": total_cases,
        "open_cases": open_cases,
        "resolved_cases": resolved_cases,
        "escalated_cases": escalated_cases,
        "has_repeat_violations": has_repeat_violations,
        "repeat_categories": repeat_categories,
        "category_breakdown": cat_rows,
        "severity_breakdown": severity_breakdown,
        "recent_cases": recent_cases,

        # Backward compatibility flat keys
        "rm_id": rm_row["rm_id"],
        "name": rm_row["full_name"],
        "branch": rm_row["branch"],
        "region": region,
        "manager_name": "Suresh Patel (Branch Head)",
        "total_violations": total_cases,
        "high_severity_count": high_count,
        "medium_severity_count": med_count,
        "low_severity_count": low_count,
        "repeat_violation_flag": has_repeat_violations,
        "repeat_violation_category": repeat_categories[0]["category"] if repeat_categories else None,
        "risk_score": risk_score,
        "trend": trend_rows,
    }


def get_rm_detail(rm_id: str) -> Optional[Dict[str, Any]]:
    """Returns detailed statistics, category breakdown, and monthly trend for an RM."""
    return get_rm_analytics(rm_id)


def get_rm_history(rm_id: str, before_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieves an RM's historical confirmed violations prior to a given call timestamp.
    Used by the Detection & Investigation agents for chronological evidence gathering.
    """
    where_sql = "c.rm_id = %s"
    params = [rm_id]

    if before_date:
        where_sql += " AND c.date_time < %s"
        params.append(before_date)

    sql = f"""
    SELECT 
        f.finding_id,
        f.call_id,
        f.category,
        f.severity,
        f.citation_label,
        f.confidence,
        f.quote_english,
        DATE_FORMAT(c.date_time, '%%Y-%%m-%%dT%%H:%%i:%%sZ') AS call_date_time
    FROM finding f
    JOIN `call` c ON f.call_id = c.id
    WHERE {where_sql}
    ORDER BY c.date_time ASC
    """

    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(params))
            findings = cur.fetchall()

    total_prior = len(findings)
    high_count = sum(1 for f in findings if f["severity"] == "HIGH")
    categories = list({f["category"] for f in findings})

    return {
        "rm_id": rm_id,
        "total_prior_violations": total_prior,
        "high_severity_prior_count": high_count,
        "prior_categories": categories,
        "has_repeat_violations": total_prior > 1,
        "findings": findings
    }
