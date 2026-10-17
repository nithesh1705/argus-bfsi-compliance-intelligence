"""
ARGUS — Ingestion Agent (backend/ingestion/ingestion_agent.py)

Orchestrates the initial ingestion pipeline:
1. Audio transcription with gemini-3.5-transcribe (diarized, timestamped, original language)
   with custom vocabulary injected from the database product catalog and regulatory terms.
2. Translation and role mapping with gemini-3.5-flash (structured Pydantic output,
   mapping diarized speakers to RM and CUSTOMER, with heuristic fallback).
3. Pre-storage PII redaction with Sensitive Data Protection (DLP), preserving exact timestamps.
4. Saves redacted segments to Cloud SQL (transcript_segment table).
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field

from backend.core.config import settings
from backend.adapters.storage import get_object_store
from backend.adapters.transcriber import get_transcriber, DiarizedSegment, TranscriptionOutput
from backend.adapters.llm import get_llm_client
from backend.adapters.pii_redactor import get_pii_redactor
from backend.db.repositories.calls_repo import (
    create_or_update_call,
    save_transcript_segments,
    get_call_by_id,
)
from backend.adapters.database import db_manager

logger = logging.getLogger("argus.ingestion.agent")


class TranslatedSegmentOutput(BaseModel):
    segment_id: int
    text_english: str


class SpeakerRoleMappingSchema(BaseModel):
    rm_speaker_label: str = Field(description="Diarization label for the Relationship Manager (e.g. 'Speaker 1')")
    customer_speaker_label: str = Field(description="Diarization label for the Customer (e.g. 'Speaker 2')")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence of role mapping")
    reasoning: str = Field(description="Brief explanation of why this mapping was determined")
    speaker_mapping_method: str = Field(default="llm")
    translated_segments: List[TranslatedSegmentOutput] = Field(default_factory=list)


def build_custom_vocabulary() -> List[str]:
    """Builds custom vocabulary from database product catalog and statutory terms."""
    vocab = [
        "SEBI", "AMFI", "NAV", "SIP", "SWP", "STP", "riskometer", "KYC",
        "AUM", "TER", "CAGR", "XIRR", "folio", "arbitrage", "duration",
        "thematic", "hybrid", "equity", "debt", "liquid fund",
    ]
    try:
        with db_manager.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT product_name FROM product")
                for r in cur.fetchall():
                    vocab.extend(r["product_name"].split())
    except Exception as exc:
        logger.warning(f"Could not load products for custom vocabulary: {exc}")
    return list(set(vocab))


def map_roles_and_translate(
    segments: List[DiarizedSegment],
    rm_name: str,
    customer_name: str,
    call_id: str,
) -> Tuple[str, str, str, Dict[int, str]]:
    """
    Uses gemini-3.5-flash with structured output to determine speaker roles (RM vs Customer)
    and produce English translations for non-English utterances.
    Falls back to heuristic (earliest first speaker = RM) on low confidence or failure.

    Returns:
        (rm_speaker_label, customer_speaker_label, mapping_method, {segment_id: text_english})
    """
    # =========================================================================
    # Speaker Role Mapping / Finding:
    # Explicitly use Gemini 2.5 Flash as requested.
    # (Rest of all LLM tasks use gemini-3.5-flash)
    # =========================================================================
    # PREVIOUS 3.5 FLASH DEFAULT:
    # llm = get_llm_client()  # gemini-3.5-flash
    llm = get_llm_client(model_id=settings.GEMINI_ROLE_MAPPING_MODEL)  # gemini-2.5-flash

    # Form prompt with explicit Segment IDs so translation and role mapping are strictly aligned
    transcript_preview = "\n".join([
        f"Segment {s.segment_id} [{s.speaker_label}]: {s.text_original} (English: {getattr(s, 'text_english', s.text_original)})"
        for s in segments
    ])

    prompt = f"""You are analyzing a Relationship Manager sales call for regulatory compliance.
Call ID: {call_id}
Relationship Manager Name: {rm_name}
Customer Name: {customer_name}

Task:
1. Determine which speaker label corresponds to the Relationship Manager ({rm_name}) and which to the Customer ({customer_name}).
2. Review the conversation. If any non-English segment needs an improved or corrected English translation, provide it with the EXACT matching 'segment_id' integer shown above.

Transcript excerpt:
{transcript_preview}
"""

    try:
        result = llm.generate_structured(
            prompt=prompt,
            response_schema=SpeakerRoleMappingSchema,
            system_instruction="Map speaker roles strictly based on speaker introduction and conversation context.",
            temperature=0.0,
        )

        # Check confidence threshold
        if result.confidence < 0.6 or not result.rm_speaker_label:
            raise ValueError(f"Low confidence ({result.confidence}) on speaker role mapping")

        translation_map = {int(t.segment_id): t.text_english for t in result.translated_segments if t.segment_id is not None}
        return (
            result.rm_speaker_label,
            result.customer_speaker_label,
            "llm",
            translation_map
        )
    except Exception as exc:
        logger.warning(f"Role mapping model fallback triggered for {call_id}: {exc}")
        # Heuristic fallback: Earliest speaking party is typically the RM initiating the call
        first_speaker = segments[0].speaker_label if segments else "Speaker 1"
        other_speaker = "Speaker 2" if first_speaker == "Speaker 1" else "Speaker 1"
        return (
            first_speaker,
            other_speaker,
            "heuristic_fallback",
            {}
        )


def process_audio_ingestion(
    audio_uri: str,
    call_id: str,
    rm_id: str,
    customer_id: str,
    product_id: Optional[str] = None,
    source_generation: str = "1",
) -> Dict[str, Any]:
    """
    Executes the complete Ingestion Stage for a call recording:
    1. Speech-to-Text & Diarization
    2. Role Mapping & Translation
    3. PII Redaction
    4. Database Persistence
    """
    logger.info(f"[Ingestion] Starting audio ingestion for {call_id} ({audio_uri})")

    # Fetch RM & Customer profiles
    rm_name = "Relationship Manager"
    customer_name = "Customer"
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT full_name FROM rm WHERE rm_id = %s", (rm_id,))
            r_row = cur.fetchone()
            if r_row:
                rm_name = r_row["full_name"]

            cur.execute("SELECT full_name FROM customer WHERE customer_id = %s", (customer_id,))
            c_row = cur.fetchone()
            if c_row:
                customer_name = c_row["full_name"]

    # 1. Transcribe
    transcriber = get_transcriber()
    vocab = build_custom_vocabulary()
    transcription: TranscriptionOutput = transcriber.transcribe(
        audio_uri=audio_uri,
        call_id=call_id,
        custom_vocabulary=vocab
    )

    if not transcription.segments:
        raise ValueError(f"Transcription returned 0 segments for {call_id}")

    # 2. Translation & Role Mapping
    rm_label, cust_label, mapping_method, trans_map = map_roles_and_translate(
        segments=transcription.segments,
        rm_name=rm_name,
        customer_name=customer_name,
        call_id=call_id
    )

    # 3. PII Redaction
    redactor = get_pii_redactor()
    processed_segments = []

    for s in transcription.segments:
        # Determine role
        role = "RM" if s.speaker_label == rm_label else "CUSTOMER"

        # English translation: fallback to segment's aligned text_english if trans_map has no override
        text_en = trans_map.get(s.segment_id) or getattr(s, "text_english", None) or s.text_original

        # Apply DLP Redaction on both original and English text
        redacted_orig = redactor.redact_text(s.text_original).redacted_text
        redacted_en = redactor.redact_text(text_en).redacted_text

        processed_segments.append({
            "idx": s.segment_id,
            "speaker_label": s.speaker_label,
            "role": role,
            "start_ms": s.start_ms,
            "end_ms": s.end_ms,
            "text_original": redacted_orig,
            "text_english": redacted_en,
            "is_violation": False,
        })

    # 4. Save call and segments
    call_record = {
        "id": call_id,
        "rm_id": rm_id,
        "customer_id": customer_id,
        "product_id": product_id,
        "gcs_uri_incoming": audio_uri,
        "gcs_uri_archive": None,
        "source_object_generation": source_generation,
        "language": transcription.language,
        "duration_s": transcription.duration_s,
        "status": "INGESTED",
        "speaker_mapping_method": mapping_method,
        "has_violation": False,
        "finding_count": 0,
        "severity": None,
        "date_time": "2026-03-10 10:30:00",
        "provider_used": transcription.provider_used,
        "is_mock": settings.is_mock(),
    }
    create_or_update_call(call_record)
    save_transcript_segments(call_id, processed_segments)

    logger.info(f"[Ingestion] Completed ingestion for {call_id}: {len(processed_segments)} segments saved.")
    return {
        "call_id": call_id,
        "status": "INGESTED",
        "segments_count": len(processed_segments),
        "duration_s": transcription.duration_s,
        "speaker_mapping_method": mapping_method,
    }
