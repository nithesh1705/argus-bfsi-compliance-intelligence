"""
ARGUS — AI Chat API Route (backend/api/routes/chat.py)
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.agents.chat_agent import process_chat_message

logger = logging.getLogger("argus.api.chat")

router = APIRouter(prefix="/chat", tags=["AI Investigation Chat"])


class ChatMessageRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    history: Optional[List[Dict[str, str]]] = Field(default_factory=list)


@router.post("/message", response_model=Dict[str, Any])
@router.post("", response_model=Dict[str, Any])
@router.post("/", response_model=Dict[str, Any])
def send_chat_message(payload: ChatMessageRequest):
    """
    Submits a user prompt to the read-only investigative compliance assistant.
    Returns the grounded reply with tools_called and grounded_results.
    Supports /api/chat, /api/chat/, and /api/chat/message.
    """
    if not payload.message or not payload.message.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message cannot be empty.")

    try:
        res = process_chat_message(
            message=payload.message.strip(),
            conversation_history=payload.history,
        )
        # Ensure field compatibility across client versions
        res["response_text"] = res.get("reply", "")
        res["tool_calls_made"] = res.get("tools_called", [])
        res["session_id"] = payload.session_id or "default"
        res["provider_used"] = "Google Cloud Gemini Flash"
        return res
    except Exception as exc:
        logger.exception(f"Chat assistant failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat assistant encountered an error: {str(exc)}"
        )
