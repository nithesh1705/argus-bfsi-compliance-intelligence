"""
ARGUS — Admin Repository (backend/db/repositories/admin_repo.py)

Powers:
1. Admin Executive Analytics & Chart Aggregations (date-range filtered time series, severity, categories, RM risk).
2. CRUD operations for Users, RMs, Customers, and Products/Funds.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import bcrypt

from backend.adapters.database import db_manager

logger = logging.getLogger("argus.db.admin")


# ==============================================================================
# Admin Analytics & Dynamic Chart Data
# ==============================================================================

def get_admin_analytics(start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Computes time-series and distribution metrics for the Admin Charts Dashboard.
    Supports start_date and end_date filtering (YYYY-MM-DD).
    """
    b = "`"
    date_filter = ""
    params: List[Any] = []

    if start_date and end_date:
        date_filter = f"WHERE DATE(c.date_time) BETWEEN %s AND %s"
        params.extend([start_date, end_date])
    elif start_date:
        date_filter = f"WHERE DATE(c.date_time) >= %s"
        params.append(start_date)
    elif end_date:
        date_filter = f"WHERE DATE(c.date_time) <= %s"
        params.append(end_date)

    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            # 1. Timeline series (calls by day)
            timeline_sql = f"""
            SELECT 
                DATE(c.date_time) AS call_day,
                COUNT(*) AS total_calls,
                SUM(CASE WHEN c.has_violation = 0 THEN 1 ELSE 0 END) AS clean_calls,
                SUM(CASE WHEN c.has_violation = 1 THEN 1 ELSE 0 END) AS violation_calls,
                COALESCE(SUM(c.finding_count), 0) AS total_findings
            FROM {b}call{b} c
            {date_filter}
            GROUP BY DATE(c.date_time)
            ORDER BY call_day ASC
            """
            cur.execute(timeline_sql, params)
            timeline_rows = cur.fetchall()

            timeline = []
            for r in timeline_rows:
                day_str = str(r["call_day"]) if r["call_day"] else "Unknown"
                timeline.append({
                    "date": day_str,
                    "total_calls": int(r["total_calls"] or 0),
                    "clean_calls": int(r["clean_calls"] or 0),
                    "violation_calls": int(r["violation_calls"] or 0),
                    "total_findings": int(r["total_findings"] or 0),
                })

            # If no calls in specified date range, provide continuous 7-day default series
            if not timeline:
                cur.execute(f"SELECT COUNT(*) AS total, SUM(CASE WHEN has_violation=0 THEN 1 ELSE 0 END) as clean, SUM(has_violation) as viol FROM {b}call{b}")
                row = cur.fetchone()
                total_c = int(row["total"] or 0)
                clean_c = int(row["clean"] or 0)
                viol_c = int(row["viol"] or 0)
                today = datetime.now()
                for i in range(6, -1, -1):
                    d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
                    timeline.append({
                        "date": d,
                        "total_calls": round(total_c / 7) if i == 0 else 0,
                        "clean_calls": round(clean_c / 7) if i == 0 else 0,
                        "violation_calls": round(viol_c / 7) if i == 0 else 0,
                        "total_findings": viol_c if i == 0 else 0,
                    })

            # 2. Total Call Stats
            cur.execute(f"SELECT COUNT(*) AS total_calls, SUM(CASE WHEN has_violation=0 THEN 1 ELSE 0 END) as clean_calls, SUM(CASE WHEN has_violation=1 THEN 1 ELSE 0 END) as violation_calls FROM {b}call{b}")
            call_stats = cur.fetchone()
            total_calls = int(call_stats["total_calls"] or 0)
            clean_calls = int(call_stats["clean_calls"] or 0)
            violation_calls = int(call_stats["violation_calls"] or 0)

            # 3. Severity breakdown
            cur.execute("SELECT severity, COUNT(*) AS count FROM finding GROUP BY severity")
            sev_rows = cur.fetchall()
            severity_profile = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
            for sr in sev_rows:
                k = (sr["severity"] or "").upper()
                if k in severity_profile:
                    severity_profile[k] = int(sr["count"] or 0)

            # 4. Finding categories breakdown
            cur.execute("SELECT category, COUNT(*) AS count FROM finding GROUP BY category ORDER BY count DESC LIMIT 8")
            categories = [{"category": r["category"], "count": int(r["count"])} for r in cur.fetchall()]

            # 5. Case Status breakdown
            cur.execute("SELECT status, COUNT(*) AS count FROM compliance_case GROUP BY status")
            case_statuses = [{"status": r["status"] or "OPEN", "count": int(r["count"])} for r in cur.fetchall()]
            total_cases = sum(cs["count"] for cs in case_statuses)

            # 6. RM Risk & Distribution
            rm_sql = f"""
            SELECT 
                r.rm_id,
                r.full_name,
                r.branch,
                COUNT(c.id) AS call_count,
                SUM(CASE WHEN c.has_violation=1 THEN 1 ELSE 0 END) AS violation_count,
                COUNT(f.finding_id) AS total_findings
            FROM rm r
            LEFT JOIN {b}call{b} c ON r.rm_id = c.rm_id
            LEFT JOIN finding f ON c.id = f.call_id
            GROUP BY r.rm_id, r.full_name, r.branch
            ORDER BY violation_count DESC, call_count DESC
            LIMIT 10
            """
            cur.execute(rm_sql)
            rm_risk = []
            for r in cur.fetchall():
                calls_cnt = int(r["call_count"] or 0)
                viols_cnt = int(r["violation_count"] or 0)
                risk_score = round((viols_cnt / calls_cnt * 100), 1) if calls_cnt > 0 else 0.0
                rm_risk.append({
                    "rm_id": r["rm_id"],
                    "name": r["full_name"],
                    "branch": r.get("branch", "Corporate"),
                    "calls": calls_cnt,
                    "violations": viols_cnt,
                    "findings": int(r["total_findings"] or 0),
                    "risk_score": risk_score,
                })

            # 7. Statutory Corpus Summary
            cur.execute("SELECT COUNT(DISTINCT document_name) AS doc_count, COUNT(*) AS chunk_count FROM regulation_chunk_registry")
            corpus_stat = cur.fetchone()

    return {
        "kpis": {
            "total_calls": total_calls,
            "clean_calls": clean_calls,
            "violation_calls": violation_calls,
            "clean_rate": round((clean_calls / total_calls * 100), 1) if total_calls > 0 else 100.0,
            "total_cases": total_cases,
            "total_findings": sum(severity_profile.values()),
            "statutory_documents": int(corpus_stat["doc_count"] or 0),
            "statutory_chunks": int(corpus_stat["chunk_count"] or 0),
        },
        "timeline": timeline,
        "severity_profile": severity_profile,
        "categories": categories,
        "case_statuses": case_statuses,
        "rm_risk": rm_risk,
    }


# ==============================================================================
# CRUD: Users
# ==============================================================================

def list_users_admin() -> List[Dict[str, Any]]:
    sql = """
    SELECT user_id, username, email, role, team, access_level, full_name, is_active, last_login_at, created_at
    FROM users
    ORDER BY created_at DESC
    """
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return [
                {
                    "user_id": r["user_id"],
                    "username": r["username"],
                    "email": r["email"],
                    "role": r["role"],
                    "team": r.get("team", "Compliance"),
                    "access_level": r.get("access_level", "All"),
                    "full_name": r.get("full_name", r["username"]),
                    "is_active": bool(r.get("is_active", True)),
                    "last_login_at": str(r["last_login_at"]) if r.get("last_login_at") else None,
                    "created_at": str(r.get("created_at", "")),
                }
                for r in cur.fetchall()
            ]


def create_user_admin(user_data: Dict[str, Any]) -> Dict[str, Any]:
    salt = bcrypt.gensalt(rounds=12)
    pwd_hash = bcrypt.hashpw(user_data["password"].encode("utf-8"), salt).decode("utf-8")
    user_id = user_data.get("user_id") or f"USR-{int(datetime.now().timestamp() * 1000) % 1000000:06d}"

    sql = """
    INSERT INTO users (user_id, username, email, password_hash, role, team, access_level, full_name, is_active)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    with db_manager.transaction() as cur:
        cur.execute(sql, (
            user_id,
            user_data["username"],
            user_data["email"],
            pwd_hash,
            user_data.get("role", "Audit Officer"),
            user_data.get("team", "Compliance"),
            user_data.get("access_level", "All"),
            user_data.get("full_name", user_data["username"]),
            user_data.get("is_active", True),
        ))

    return {
        "user_id": user_id,
        "username": user_data["username"],
        "email": user_data["email"],
        "role": user_data.get("role", "Audit Officer"),
        "full_name": user_data.get("full_name", user_data["username"]),
    }


def update_user_admin(user_id: str, updates: Dict[str, Any]) -> bool:
    fields = []
    params = []
    for k in ["username", "email", "role", "team", "access_level", "full_name", "is_active"]:
        if k in updates and updates[k] is not None:
            fields.append(f"{k} = %s")
            params.append(updates[k])

    if "password" in updates and updates["password"]:
        salt = bcrypt.gensalt(rounds=12)
        pwd_hash = bcrypt.hashpw(updates["password"].encode("utf-8"), salt).decode("utf-8")
        fields.append("password_hash = %s")
        params.append(pwd_hash)

    if not fields:
        return False

    params.append(user_id)
    sql = f"UPDATE users SET {', '.join(fields)} WHERE user_id = %s"
    with db_manager.transaction() as cur:
        cur.execute(sql, params)
    return True


def delete_user_admin(user_id: str) -> bool:
    sql = "DELETE FROM users WHERE user_id = %s"
    with db_manager.transaction() as cur:
        cur.execute(sql, (user_id,))
    return True


# ==============================================================================
# CRUD: Relationship Managers (RMs)
# ==============================================================================

def list_rms_admin() -> List[Dict[str, Any]]:
    sql = "SELECT rm_id, full_name, branch, joined_date, active FROM rm ORDER BY rm_id ASC"
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return [
                {
                    "rm_id": r["rm_id"],
                    "full_name": r["full_name"],
                    "branch": r.get("branch", ""),
                    "joined_date": str(r["joined_date"]) if r.get("joined_date") else None,
                    "active": bool(r.get("active", True)),
                }
                for r in cur.fetchall()
            ]


def create_rm_admin(rm_data: Dict[str, Any]) -> Dict[str, Any]:
    rm_id = rm_data.get("rm_id") or f"RM-{int(datetime.now().timestamp()) % 1000:03d}"
    joined = rm_data.get("joined_date") or datetime.now().strftime("%Y-%m-%d")
    sql = "INSERT INTO rm (rm_id, full_name, branch, joined_date, active) VALUES (%s, %s, %s, %s, %s)"
    with db_manager.transaction() as cur:
        cur.execute(sql, (
            rm_id,
            rm_data["full_name"],
            rm_data.get("branch", "Main Branch"),
            joined,
            rm_data.get("active", True),
        ))
    return {"rm_id": rm_id, "full_name": rm_data["full_name"], "branch": rm_data.get("branch", "")}


def update_rm_admin(rm_id: str, updates: Dict[str, Any]) -> bool:
    fields = []
    params = []
    for k in ["full_name", "branch", "joined_date", "active"]:
        if k in updates and updates[k] is not None:
            fields.append(f"{k} = %s")
            params.append(updates[k])

    if not fields:
        return False

    params.append(rm_id)
    sql = f"UPDATE rm SET {', '.join(fields)} WHERE rm_id = %s"
    with db_manager.transaction() as cur:
        cur.execute(sql, params)
    return True


def delete_rm_admin(rm_id: str) -> bool:
    sql = "DELETE FROM rm WHERE rm_id = %s"
    with db_manager.transaction() as cur:
        cur.execute(sql, (rm_id,))
    return True


# ==============================================================================
# CRUD: Customers
# ==============================================================================

def list_customers_admin() -> List[Dict[str, Any]]:
    sql = "SELECT customer_id, full_name, mobile_number, risk_profile, investment_experience, kyc_status FROM customer ORDER BY customer_id ASC"
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return [
                {
                    "customer_id": r["customer_id"],
                    "full_name": r["full_name"],
                    "mobile_number": r.get("mobile_number", ""),
                    "risk_profile": r.get("risk_profile", "Moderate"),
                    "investment_experience": r.get("investment_experience", "Intermediate"),
                    "kyc_status": r.get("kyc_status", "VERIFIED"),
                }
                for r in cur.fetchall()
            ]


def create_customer_admin(cust_data: Dict[str, Any]) -> Dict[str, Any]:
    cust_id = cust_data.get("customer_id") or f"CUST-{int(datetime.now().timestamp()) % 10000:04d}"
    sql = """
    INSERT INTO customer (customer_id, full_name, mobile_number, risk_profile, investment_experience, kyc_status)
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    with db_manager.transaction() as cur:
        cur.execute(sql, (
            cust_id,
            cust_data["full_name"],
            cust_data.get("mobile_number", "+91 98765 00000"),
            cust_data.get("risk_profile", "Moderate"),
            cust_data.get("investment_experience", "Intermediate"),
            cust_data.get("kyc_status", "VERIFIED"),
        ))
    return {"customer_id": cust_id, "full_name": cust_data["full_name"]}


def update_customer_admin(customer_id: str, updates: Dict[str, Any]) -> bool:
    fields = []
    params = []
    for k in ["full_name", "mobile_number", "risk_profile", "investment_experience", "kyc_status"]:
        if k in updates and updates[k] is not None:
            fields.append(f"{k} = %s")
            params.append(updates[k])

    if not fields:
        return False

    params.append(customer_id)
    sql = f"UPDATE customer SET {', '.join(fields)} WHERE customer_id = %s"
    with db_manager.transaction() as cur:
        cur.execute(sql, params)
    return True


def delete_customer_admin(customer_id: str) -> bool:
    sql = "DELETE FROM customer WHERE customer_id = %s"
    with db_manager.transaction() as cur:
        cur.execute(sql, (customer_id,))
    return True


# ==============================================================================
# CRUD: Products / Funds
# ==============================================================================

def list_products_admin() -> List[Dict[str, Any]]:
    sql = "SELECT product_id, product_name, risk_class, suitable_risk_profiles, disclosure_requirements FROM product ORDER BY product_id ASC"
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return [
                {
                    "product_id": r["product_id"],
                    "product_name": r["product_name"],
                    "risk_class": r.get("risk_class", "Moderate Risk"),
                    "suitable_risk_profiles": r.get("suitable_risk_profiles", "Moderate, Aggressive"),
                    "disclosure_requirements": r.get("disclosure_requirements", ""),
                }
                for r in cur.fetchall()
            ]


def create_product_admin(prod_data: Dict[str, Any]) -> Dict[str, Any]:
    prod_id = prod_data.get("product_id") or f"PRD-{int(datetime.now().timestamp()) % 1000:03d}"
    sql = """
    INSERT INTO product (product_id, product_name, risk_class, suitable_risk_profiles, disclosure_requirements)
    VALUES (%s, %s, %s, %s, %s)
    """
    with db_manager.transaction() as cur:
        cur.execute(sql, (
            prod_id,
            prod_data["product_name"],
            prod_data.get("risk_class", "Moderate Risk"),
            prod_data.get("suitable_risk_profiles", "Moderate, Aggressive"),
            prod_data.get("disclosure_requirements", "Standard SEBI MF Scheme Information Document"),
        ))
    return {"product_id": prod_id, "product_name": prod_data["product_name"]}


def update_product_admin(product_id: str, updates: Dict[str, Any]) -> bool:
    fields = []
    params = []
    for k in ["product_name", "risk_class", "suitable_risk_profiles", "disclosure_requirements"]:
        if k in updates and updates[k] is not None:
            fields.append(f"{k} = %s")
            params.append(updates[k])

    if not fields:
        return False

    params.append(product_id)
    sql = f"UPDATE product SET {', '.join(fields)} WHERE product_id = %s"
    with db_manager.transaction() as cur:
        cur.execute(sql, params)
    return True


def delete_product_admin(product_id: str) -> bool:
    sql = "DELETE FROM product WHERE product_id = %s"
    with db_manager.transaction() as cur:
        cur.execute(sql, (product_id,))
    return True


# ==============================================================================
# CRUD: Regulatory Authorities (SEBI, AMFI, RBI, etc.)
# ==============================================================================

def list_authorities_admin(active_only: bool = False) -> List[Dict[str, Any]]:
    """Lists all regulatory authorities with associated document counts."""
    where_clause = "WHERE a.active = TRUE" if active_only else ""
    sql = f"""
    SELECT 
        a.authority_id,
        a.name,
        a.short_code,
        a.jurisdiction,
        a.website_url,
        a.description,
        a.active,
        a.created_at,
        COUNT(d.document_id) AS document_count
    FROM regulatory_authority a
    LEFT JOIN regulatory_documents d ON (
        UPPER(d.regulator) = UPPER(a.short_code) OR UPPER(d.regulator) = UPPER(a.authority_id)
    )
    {where_clause}
    GROUP BY 
        a.authority_id, a.name, a.short_code, a.jurisdiction, 
        a.website_url, a.description, a.active, a.created_at
    ORDER BY a.short_code ASC
    """
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            return [
                {
                    "authority_id": r["authority_id"],
                    "name": r["name"],
                    "short_code": r["short_code"],
                    "jurisdiction": r.get("jurisdiction") or "India",
                    "website_url": r.get("website_url") or "",
                    "description": r.get("description") or "",
                    "active": bool(r.get("active", True)),
                    "created_at": r["created_at"].isoformat() if hasattr(r.get("created_at"), "isoformat") else str(r.get("created_at") or ""),
                    "document_count": int(r.get("document_count") or 0),
                }
                for r in rows
            ]


def create_authority_admin(auth_data: Dict[str, Any]) -> Dict[str, Any]:
    """Creates a new regulatory authority."""
    short_code = (auth_data.get("short_code") or auth_data.get("authority_id") or "").strip().upper()
    if not short_code:
        raise ValueError("Authority Short Code is required (e.g. SEBI, AMFI, RBI)")

    authority_id = (auth_data.get("authority_id") or short_code).strip().upper()
    name = (auth_data.get("name") or short_code).strip()
    jurisdiction = auth_data.get("jurisdiction") or "India"
    website_url = auth_data.get("website_url") or ""
    description = auth_data.get("description") or ""
    active = bool(auth_data.get("active", True))

    sql = """
    INSERT INTO regulatory_authority (
        authority_id, short_code, name, jurisdiction, website_url, description, active
    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    with db_manager.transaction() as cur:
        cur.execute(sql, (authority_id, short_code, name, jurisdiction, website_url, description, active))

    return {
        "authority_id": authority_id,
        "short_code": short_code,
        "name": name,
        "jurisdiction": jurisdiction,
        "website_url": website_url,
        "description": description,
        "active": active,
        "document_count": 0,
    }


def update_authority_admin(authority_id: str, updates: Dict[str, Any]) -> bool:
    """Updates an existing regulatory authority."""
    fields = []
    params = []
    allowed = ["name", "short_code", "jurisdiction", "website_url", "description", "active"]
    for k in allowed:
        if k in updates and updates[k] is not None:
            fields.append(f"{k} = %s")
            params.append(updates[k])

    if not fields:
        return False

    params.append(authority_id)
    sql = f"UPDATE regulatory_authority SET {', '.join(fields)} WHERE authority_id = %s"
    with db_manager.transaction() as cur:
        cur.execute(sql, params)
    return True


def delete_authority_admin(authority_id: str) -> bool:
    """Deletes or unregisters a regulatory authority."""
    sql = "DELETE FROM regulatory_authority WHERE authority_id = %s"
    with db_manager.transaction() as cur:
        cur.execute(sql, (authority_id,))
    return True

