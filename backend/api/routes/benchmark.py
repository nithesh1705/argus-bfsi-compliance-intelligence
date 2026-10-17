"""
ARGUS — Benchmark Results API Route (backend/api/routes/benchmark.py)
"""

import json
from pathlib import Path
from typing import Dict, Any
from fastapi import APIRouter

from backend.benchmark.run_benchmark import run_benchmark_evaluation, REPORT_JSON_FILE

router = APIRouter(prefix="/benchmark", tags=["Benchmark"])


@router.get("", response_model=Dict[str, Any])
def get_benchmark_report():
    """Returns the latest three-way benchmark evaluation report."""
    if REPORT_JSON_FILE.exists():
        try:
            with open(REPORT_JSON_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return run_benchmark_evaluation()
