"""
ARGUS — Database Repositories Package (backend/db/repositories/__init__.py)
"""

from backend.db.repositories.calls_repo import (
    create_or_update_call,
    save_transcript_segments,
    get_call_by_id,
    list_calls,
)
from backend.db.repositories.cases_repo import (
    list_cases,
    get_case_detail,
    update_case_status,
    escalate_case,
    assign_case,
    add_case_note,
    get_current_confidence_threshold,
    CaseNotFoundError,
    CaseAlreadyResolvedError,
    CaseAlreadyEscalatedError,
    ReviewerNotFoundError,
)
from backend.db.repositories.rm_repo import (
    get_rm_list_with_stats,
    get_rm_detail,
    get_rm_history,
)
from backend.db.repositories.dashboard_repo import (
    get_dashboard_summary,
    get_pipeline_latency_summary,
)
from backend.db.repositories.regulations_repo import (
    batch_upsert_chunks,
    list_documents,
    get_chunk,
)
from backend.db.repositories.findings_repo import (
    commit_confirmed_finding,
    list_findings,
)

__all__ = [
    "create_or_update_call",
    "save_transcript_segments",
    "get_call_by_id",
    "list_calls",
    "list_cases",
    "get_case_detail",
    "update_case_status",
    "escalate_case",
    "assign_case",
    "add_case_note",
    "get_current_confidence_threshold",
    "CaseNotFoundError",
    "CaseAlreadyResolvedError",
    "CaseAlreadyEscalatedError",
    "ReviewerNotFoundError",
    "get_rm_list_with_stats",
    "get_rm_detail",
    "get_rm_history",
    "get_dashboard_summary",
    "get_pipeline_latency_summary",
    "batch_upsert_chunks",
    "list_documents",
    "get_chunk",
    "commit_confirmed_finding",
    "list_findings",
]
