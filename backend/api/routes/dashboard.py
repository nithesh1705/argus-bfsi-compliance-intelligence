"""
ARGUS — Dashboard API Route (backend/api/routes/dashboard.py)
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter

from backend.db.repositories.dashboard_repo import get_dashboard_summary

logger = logging.getLogger("argus.api.dashboard")

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=Dict[str, Any])
def dashboard_summary():
    """Returns high-density KPIs, trends, category breakdown, recent cases, and real latency stats."""
    return get_dashboard_summary()
