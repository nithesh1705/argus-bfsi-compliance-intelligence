"""
ARGUS — Eventarc / Pub/Sub Push Receiver & Pipeline Triggers (backend/api/routes/events.py)

Endpoints:
- POST /events/gcs: Receives Pub/Sub push messages triggered by Eventarc GCS finalize events.
- POST /api/pipeline/process-now: Reviewer-triggered on-demand processing endpoint.
"""

import json
import base64
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, Header, HTTPException, status, BackgroundTasks
from pydantic import BaseModel

from backend.core.config import settings
from backend.ingestion.pipeline_runner import run_pipeline_for_object

logger = logging.getLogger("argus.api.events")

# Router mounted at root for Eventarc /events/gcs and /api/pipeline/process-now
router = APIRouter(tags=["Events & Pipeline"])


class ProcessNowRequest(BaseModel):
    object_name: str


def verify_oidc_token(auth_header: Optional[str]) -> bool:
    """
    Validates Google OIDC bearer token from Eventarc/Pub-Sub against configured service account.
    Bypassed in mock or development mode.
    """
    if settings.is_mock() or settings.ENVIRONMENT == "development":
        return True

    if not auth_header or not auth_header.startswith("Bearer "):
        logger.warning("Missing or malformed Authorization header on /events/gcs")
        return False

    token = auth_header.split(" ")[1]
    # TODO(PHASE2-VERIFY): Verify google.oauth2.id_token.verify_oauth2_token with target Cloud Run audience
    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests

        claims = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            audience=settings.OIDC_AUDIENCE
        )

        email = claims.get("email")
        if email not in settings.ALLOWED_SERVICE_ACCOUNTS:
            logger.warning(f"Unauthorized service account '{email}' attempted event push")
            return False
        return True
    except Exception as exc:
        logger.error(f"OIDC token verification failed: {exc}")
        return False


@router.post("/events/gcs", status_code=status.HTTP_200_OK)
async def handle_gcs_finalize_event(
    request: Request,
    background_tasks: BackgroundTasks,
    authorization: Optional[str] = Header(None)
):
    """
    Receives Pub/Sub push messages wrapping Eventarc GCS finalize notifications.
    Returns HTTP 200 immediately and executes pipeline in a background task to prevent event-loop blocking.
    """
    if not verify_oidc_token(authorization):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or unauthorized OIDC token for Pub/Sub push"
        )

    try:
        body = await request.json()
    except Exception:
        # Invalid JSON: Return 200 to ack and prevent redelivery loop
        logger.error("Malformed JSON payload received on /events/gcs. Acking to prevent storm.")
        return {"status": "ACK_INVALID_JSON"}

    # Extract Pub/Sub message payload
    message = body.get("message", {})
    data_b64 = message.get("data")
    if not data_b64:
        logger.warning("Empty data payload in Pub/Sub message. Acking.")
        return {"status": "ACK_EMPTY_MESSAGE"}

    try:
        data_json = json.loads(base64.b64decode(data_b64).decode("utf-8"))
    except Exception as exc:
        logger.error(f"Failed decoding Pub/Sub data base64: {exc}")
        return {"status": "ACK_DECODE_ERROR"}

    # Extract GCS event details
    object_name = data_json.get("name")
    bucket_name = data_json.get("bucket")
    generation = str(data_json.get("generation", "1"))

    if not object_name:
        logger.warning("GCS event missing 'name' attribute. Acking.")
        return {"status": "ACK_MISSING_NAME"}

    # Only process recordings dropped into incoming/
    if not ("calls/incoming" in object_name or object_name.startswith("RM")):
        logger.info(f"Ignoring non-incoming object finalize: {object_name}")
        return {"status": "ACK_IGNORED_PATH"}

    # Clean object name (e.g. calls/incoming/RM001...wav -> RM001...wav)
    clean_object_name = object_name.split("/")[-1]

    logger.info(f"[Events] Received GCS finalize for {clean_object_name} (gen {generation}) in {bucket_name}")

    # Schedule background execution to prevent blocking uvicorn event loop and prevent Pub/Sub timeout
    background_tasks.add_task(
        run_pipeline_for_object,
        object_name=clean_object_name,
        bucket_name=bucket_name,
        generation=generation,
    )

    return {"status": "ACK_SCHEDULED", "object_name": clean_object_name}


@router.post("/api/pipeline/process-now", status_code=status.HTTP_200_OK)
def trigger_process_now(payload: ProcessNowRequest, background_tasks: BackgroundTasks):
    """
    On-demand API endpoint for reviewer-triggered processing of an audio recording.
    """
    clean_name = payload.object_name.split("/")[-1]
    logger.info(f"[API] Manual process-now triggered for {clean_name}")

    background_tasks.add_task(run_pipeline_for_object, clean_name)
    return {"status": "SCHEDULED", "object_name": clean_name}
