"""
ARGUS — Compliance Case Repository Compatibility Alias (backend/db/repositories/compliance_repo.py)
Re-exports cases_repo functions and defines create_compliance_case helper for compliance test suites.
"""

from typing import Optional
from backend.adapters.database import db_manager
from backend.db.repositories.cases_repo import *


def create_compliance_case(
    case_id: str,
    call_id: str,
    finding_id: Optional[str] = None,
    rm_id: str = "RM001",
    customer_id: str = "CUST001",
    category: str = "GUARANTEED_RETURN",
    severity: str = "HIGH",
    status: str = "NEW",
    cur=None
):
    sql = """
    INSERT INTO compliance_case (case_id, finding_id, call_id, rm_id, customer_id, category, severity, status, escalated)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, FALSE)
    """
    if cur:
        cur.execute(sql, (case_id, finding_id, call_id, rm_id, customer_id, category, severity, status))
    else:
        with db_manager.transaction() as c:
            c.execute(sql, (case_id, finding_id, call_id, rm_id, customer_id, category, severity, status))
