"""
ARGUS — Calls API Routes (backend/api/routes/calls.py)

Exposes:
- GET /api/calls: Filterable call list from Cloud SQL
- GET /api/calls/{call_id}: Full call detail including transcript segments
- GET /api/calls/{call_id}/audio: Streams audio from ObjectStore with HTTP Range (206) support
"""

import io
import re
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Header, Response, status
from fastapi.responses import StreamingResponse

from backend.core.config import settings
from backend.adapters.storage import get_object_store
from backend.db.repositories.calls_repo import list_calls, get_call_by_id

logger = logging.getLogger("argus.api.calls")

router = APIRouter(prefix="/calls", tags=["Calls"])


@router.get("", response_model=Dict[str, Any])
def get_calls(
    rm_id: Optional[str] = Query(None),
    customer_id: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    has_violation: Optional[bool] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Retrieve paginated calls with filters from Cloud SQL."""
    return list_calls(
        rm_id=rm_id,
        customer_id=customer_id,
        severity=severity,
        status_filter=status_filter,
        has_violation=has_violation,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )


@router.get("/{call_id}", response_model=Dict[str, Any])
def get_call_detail(call_id: str):
    """Retrieve full call detail with transcript segments."""
    call = get_call_by_id(call_id)
    if not call:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Call '{call_id}' not found.")
    return call


@router.get("/{call_id}/audio")
def stream_call_audio(
    call_id: str,
    range: Optional[str] = Header(None)
):
    """
    Streams audio recording for a call through the backend from ObjectStore (GCS or local)
    with HTTP 206 Partial Content support for WaveSurfer audio seeking.
    """
    call = get_call_by_id(call_id)
    clean_name = call_id.replace("CALL_", "")
    filename = f"{clean_name}.wav"

    store = get_object_store()

    # Locate audio key in archive or incoming
    possible_keys = [
        f"calls/archive/{filename}",
        f"calls/incoming/{filename}",
        f"calls/archive/{clean_name}.mp3",
        f"calls/incoming/{clean_name}.mp3",
    ]

    found_key = None
    for k in possible_keys:
        meta = store.get_metadata(k)
        if meta:
            found_key = k
            break

    if not found_key:
        # Check if call record has archive uri
        if call and call.get("gcs_uri_archive"):
            found_key = call["gcs_uri_archive"]
        else:
            # Fallback: check any file in incoming or archive matching call id
            arch_objs = store.list_objects("calls/archive")
            for obj in arch_objs:
                if clean_name in obj:
                    found_key = obj
                    break

    if not found_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Audio file for call '{call_id}' not found in storage.")

    # Read audio bytes
    try:
        audio_bytes = store.read_bytes(found_key)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Error reading audio: {exc}")

    total_size = len(audio_bytes)
    content_type = "audio/wav" if found_key.endswith(".wav") else "audio/mpeg"

    # Handle HTTP Range Header (HTTP 206 Partial Content)
    if range:
        match = re.match(r"bytes=(\d+)-(\d*)", range)
        if match:
            start = int(match.group(1))
            end_group = match.group(2)
            end = int(end_group) if end_group else total_size - 1

            if start >= total_size:
                raise HTTPException(status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE)

            end = min(end, total_size - 1)
            chunk_length = end - start + 1
            chunk_data = audio_bytes[start:start + chunk_length]

            headers = {
                "Content-Range": f"bytes {start}-{end}/{total_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(chunk_length),
                "Content-Type": content_type,
            }
            return Response(content=chunk_data, status_code=status.HTTP_206_PARTIAL_CONTENT, headers=headers)

    # Full response
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(total_size),
        "Content-Type": content_type,
    }
    return Response(content=audio_bytes, status_code=status.HTTP_200_OK, headers=headers)
