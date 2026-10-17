"""
ARGUS — Relationship Manager Analytics & Reporting API Routes (backend/api/routes/rm.py)
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.db.repositories.rm_repo import get_rm_list_with_stats, get_rm_detail, get_rm_analytics
from backend.reports.rm_report_service import get_rm_report_data, record_report_audit, check_idempotency
from backend.reports.rm_report_renderer import render_rm_report_html, render_rm_report_text
from backend.reports.email_service import send_email, validate_recipients, EmailServiceError

logger = logging.getLogger("argus.api.rm")

router = APIRouter(prefix="/rm", tags=["Relationship Managers"])


class SendReportRequest(BaseModel):
    recipients: List[str] = Field(..., min_items=1, description="Target recipient email addresses")
    request_id: Optional[str] = Field(None, description="Client-generated idempotency request ID")


class SendReportResponse(BaseModel):
    success: bool
    rm_id: str
    recipients: List[str]
    sent_at: str
    report_id: str
    idempotent_replay: Optional[bool] = False


@router.get("", response_model=List[Dict[str, Any]])
def list_rms():
    """Returns RM roster with aggregate surveillance stats and computed risk scores."""
    return get_rm_list_with_stats()


@router.get("/{rm_id}/analytics", response_model=Dict[str, Any])
def get_rm_analytics_route(rm_id: str):
    """Returns complete dossier analytics, telemetry, and case breakdown for an RM."""
    dossier = get_rm_analytics(rm_id)
    if not dossier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Relationship Manager dossier '{rm_id}' not found."
        )
    return dossier


@router.get("/{rm_id}", response_model=Dict[str, Any])
def get_rm(rm_id: str):
    """Returns detailed statistics, trend, and category breakdown for an RM."""
    dossier = get_rm_detail(rm_id)
    if not dossier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Relationship Manager '{rm_id}' not found."
        )
    return dossier


@router.post("/{rm_id}/report/email", response_model=SendReportResponse)
async def send_rm_report_email(rm_id: str, payload: SendReportRequest):
    """
    Generate and dispatch the authoritative HTML compliance report for an RM.
    Includes idempotency safeguards and recipient domain classification.
    """
    # 1. Idempotency replay check
    if payload.request_id:
        cached = check_idempotency(payload.request_id)
        if cached:
            logger.info(f"Idempotent replay detected for request_id={payload.request_id}")
            return SendReportResponse(**cached, idempotent_replay=True)

    # 2. Validate recipients
    clean_recipients, domain_class = validate_recipients(payload.recipients)

    # 3. Assemble report dataset
    report_data = get_rm_report_data(rm_id)
    if not report_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cannot generate compliance report: RM '{rm_id}' does not exist."
        )

    report_id = report_data.get("report_id", f"REP-{rm_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}")
    sent_at = datetime.now(timezone.utc).isoformat()
    rm_name = report_data.get("rm", {}).get("full_name", rm_id)

    # 4. Render HTML and plain text bodies
    html_body = render_rm_report_html(report_data)
    plain_text = render_rm_report_text(report_data)

    subject = f"[ARGUS Compliance Dossier] Surveillance Audit Report — {rm_name} ({rm_id})"

    # 5. Dispatch email via SMTP (or configured connector)
    try:
        dispatch_res = await send_email(
            recipients=clean_recipients,
            subject=subject,
            html_body=html_body,
            plain_text=plain_text,
        )
        logger.info(f"Report {report_id} dispatched via {dispatch_res.get('provider')} to {len(clean_recipients)} recipient(s)")
    except EmailServiceError as err:
        logger.error(f"Outbound email dispatch failed: {err.message}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Email delivery failed: {err.message}"
        )

    response_data = {
        "success": True,
        "rm_id": rm_id,
        "recipients": clean_recipients,
        "sent_at": sent_at,
        "report_id": report_id,
        "idempotent_replay": False,
    }

    # 6. Record audit & cache for idempotency
    record_report_audit(payload.request_id, response_data)

    return SendReportResponse(**response_data)
