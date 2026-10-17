"""
ARGUS — Compliance Cases API Routes (backend/api/routes/cases.py)

Exposes:
- GET /api/cases: Filterable case list with dynamically computed needs_review flag
- GET /api/cases/{case_id}: Assembled full Evidence Chain
- PATCH /api/cases/{case_id}/status: Atomic mark_reviewed / dismiss
- POST /api/cases/{case_id}/escalate: Committee escalation
- POST /api/cases/{case_id}/assign: Idempotent reviewer assignment
- POST /api/cases/{case_id}/notes: Append audit notes
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.db.repositories.cases_repo import (
    list_cases,
    get_case_detail,
    update_case_status,
    escalate_case,
    assign_case,
    add_case_note,
    CaseNotFoundError,
    CaseAlreadyResolvedError,
    CaseAlreadyEscalatedError,
    ReviewerNotFoundError,
)

logger = logging.getLogger("argus.api.cases")

router = APIRouter(prefix="/cases", tags=["Cases"])


class CaseStatusUpdateRequest(BaseModel):
    reviewer_id: str
    action: str  # "mark_reviewed" | "dismiss"
    notes: Optional[str] = None


class CaseEscalateRequest(BaseModel):
    reviewer_id: str
    notes: Optional[str] = None


class CaseAssignRequest(BaseModel):
    reviewer_id: str
    assignee_reviewer_id: Optional[str] = None
    assigned_to: Optional[str] = None

    @property
    def target_reviewer(self) -> str:
        return self.assignee_reviewer_id or self.assigned_to or self.reviewer_id


class CaseNoteRequest(BaseModel):
    reviewer_id: str
    notes: Optional[str] = None
    note_text: Optional[str] = None

    @property
    def note_content(self) -> str:
        return self.notes or self.note_text or ""


class CaseResolveRequest(BaseModel):
    reviewer_id: str
    action: str  # "DISMISSED" | "mark_reviewed" | "dismiss" | "reviewed"
    rationale: Optional[str] = None
    notes: Optional[str] = None


@router.get("", response_model=Dict[str, Any])
def get_cases(
    status_filter: Optional[str] = Query(None, alias="status"),
    severity: Optional[str] = Query(None),
    rm_id: Optional[str] = Query(None),
    call_id: Optional[str] = Query(None),
    needs_review: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Retrieve cases with status/severity/rm/call_id filtering and dynamic needs_review."""
    return list_cases(
        status_filter=status_filter,
        severity=severity,
        rm_id=rm_id,
        call_id=call_id,
        needs_review=needs_review,
        limit=limit,
        offset=offset,
    )


@router.get("/{case_id}", response_model=Dict[str, Any])
def get_single_case(case_id: str):
    """Assemble and return the complete Evidence Chain for a case."""
    case = get_case_detail(case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case '{case_id}' not found.")
    return case


@router.patch("/{case_id}/status", response_model=Dict[str, Any])
def patch_case_status(case_id: str, payload: CaseStatusUpdateRequest):
    """
    Atomically transition case status to RESOLVED ('mark_reviewed' or 'dismiss').
    Returns HTTP 409 if case is already resolved.
    """
    try:
        return update_case_status(
            case_id=case_id,
            reviewer_id=payload.reviewer_id,
            action=payload.action,
            notes=payload.notes,
        )
    except CaseAlreadyResolvedError as care:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "CASE_ALREADY_RESOLVED", "message": str(care), "case_id": case_id}
        )
    except CaseNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case '{case_id}' not found.")


@router.post("/{case_id}/escalate", response_model=Dict[str, Any])
def post_escalate_case(case_id: str, payload: CaseEscalateRequest):
    """
    Escalate a compliance case to the committee.
    Returns HTTP 409 if already escalated.
    """
    try:
        return escalate_case(
            case_id=case_id,
            reviewer_id=payload.reviewer_id,
            notes=payload.notes,
        )
    except CaseAlreadyEscalatedError as caee:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "CASE_ALREADY_ESCALATED", "message": str(caee), "case_id": case_id}
        )
    except CaseNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case '{case_id}' not found.")


@router.post("/{case_id}/assign", response_model=Dict[str, Any])
def post_assign_case(case_id: str, payload: CaseAssignRequest):
    """Assign or reassign a compliance case to a reviewer."""
    try:
        return assign_case(
            case_id=case_id,
            reviewer_id=payload.reviewer_id,
            assignee_reviewer_id=payload.target_reviewer,
        )
    except ReviewerNotFoundError as rnfe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(rnfe))
    except CaseNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case '{case_id}' not found.")


@router.post("/{case_id}/notes", response_model=Dict[str, Any])
def post_add_note(case_id: str, payload: CaseNoteRequest):
    """Append an audit note to the case activity log."""
    try:
        return add_case_note(
            case_id=case_id,
            reviewer_id=payload.reviewer_id,
            notes=payload.note_content,
        )
    except CaseNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case '{case_id}' not found.")


@router.post("/{case_id}/resolve", response_model=Dict[str, Any])
def post_resolve_case(case_id: str, payload: CaseResolveRequest):
    """
    Atomically transition case status to RESOLVED via POST /resolve.
    Returns HTTP 409 if case is already resolved.
    """
    act = payload.action.lower()
    if "dismiss" in act:
        normalized_action = "dismiss"
    else:
        normalized_action = "mark_reviewed"
    note_str = payload.rationale or payload.notes or "Resolved via API"
    try:
        return update_case_status(
            case_id=case_id,
            reviewer_id=payload.reviewer_id,
            action=normalized_action,
            notes=note_str,
        )
    except CaseAlreadyResolvedError as care:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "CASE_ALREADY_RESOLVED", "message": str(care), "case_id": case_id}
        )
    except CaseNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case '{case_id}' not found.")
