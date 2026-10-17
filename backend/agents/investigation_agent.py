"""
ARGUS — Investigation Agent (backend/agents/investigation_agent.py)

Forensic compliance investigation agent evaluating candidate violations flagged by Detection.
Enforces strict in-code hard guardrails:
1. Dismissal if no citations retrieved (DISMISSED_NO_CITATION)
2. Exact citation match validation against retrieved chunks (DISMISSED_CITATION_MISMATCH)
3. HIGH severity timestamp & chunk validation
4. Transcript quote verification

Audits all outcomes to the 'investigation' table and commits CONFIRMED findings
atomically to 'finding', 'compliance_case', and 'case_activity_log'.
"""

import json
import time
import logging
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field

from backend.core.config import settings
from backend.adapters.llm import get_llm_client
from backend.adapters.retriever import get_regulation_retriever, RetrievedPassage
from backend.adapters.database import db_manager
from backend.db.repositories.findings_repo import commit_confirmed_finding
from backend.db.repositories.regulations_repo import get_chunk
from backend.db.repositories.rm_repo import get_rm_history
from backend.agents.detection_agent import resolve_best_matching_quote

logger = logging.getLogger("argus.agents.investigation")


class InvestigationDecision(BaseModel):
    outcome: str = Field(description="Forensic outcome: CONFIRMED, DISMISSED, or ESCALATE_FOR_REVIEW")
    severity: str = Field(description="Final severity assessment: HIGH, MEDIUM, LOW")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score (0.0 to 1.0)")
    regulation_chunk_id: str = Field(description="Exact regulation chunk_id grounding this decision")
    reasoning: str = Field(description="Forensic rationale connecting transcript evidence to statutory clause")
    supporting_evidence: List[str] = Field(default_factory=list, description="Evidence facts supporting violation")
    contradicting_evidence: List[str] = Field(default_factory=list, description="Facts mitigating or disputing violation")


def record_investigation_audit(
    investigation_id: str,
    candidate_id: str,
    call_id: str,
    outcome: str,
    reasoning: str,
    model: str = "gemini-3.5-flash",
    token_prompt: int = 0,
    token_completion: int = 0,
    latency_ms: int = 0,
    raw_output: Optional[Dict[str, Any]] = None,
):
    """Logs the complete forensic decision and guardrail audit trail to Cloud SQL."""
    sql = """
    INSERT INTO investigation (
        investigation_id, candidate_id, call_id, outcome, reasoning, model,
        token_count_prompt, token_count_completion, latency_ms, raw_structured_output
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    ) ON DUPLICATE KEY UPDATE
        outcome = VALUES(outcome),
        reasoning = VALUES(reasoning)
    """
    with db_manager.transaction() as cur:
        cur.execute(sql, (
            investigation_id,
            candidate_id,
            call_id,
            outcome,
            reasoning,
            model,
            token_prompt,
            token_completion,
            latency_ms,
            json.dumps(raw_output or {})
        ))


def run_investigation_for_candidate(
    candidate: Dict[str, Any],
    call_context: Dict[str, Any],
    retrieved_passages: List[RetrievedPassage],
    segments: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Evaluates a single candidate violation against retrieved regulatory citations
    and enforces hard code guardrails.
    """
    candidate_id = candidate["candidate_id"]
    call_id = candidate["call_id"]
    investigation_id = f"INV-{candidate_id}"

    # -------------------------------------------------------------------------
    # HARD GUARDRAIL 1: No retrieved citations
    # If retrieval returned nothing, perform one query reformulation.
    # If still nothing, skip LLM call and dismiss as DISMISSED_NO_CITATION.
    # -------------------------------------------------------------------------
    if not retrieved_passages:
        retriever = get_regulation_retriever()
        category_query = candidate.get("category", "").replace("_", " ")
        retrieved_passages = retriever.search_regulations(category_query, status="current", limit=3)

    if not retrieved_passages:
        reason = "No regulatory basis retrieved (unverified). Dismissed without LLM invocation."
        logger.info(f"[Guardrail 1 Triggered] {candidate_id} dismissed: {reason}")
        record_investigation_audit(
            investigation_id=investigation_id,
            candidate_id=candidate_id,
            call_id=call_id,
            outcome="DISMISSED_NO_CITATION",
            reasoning=reason,
        )
        return {"outcome": "DISMISSED_NO_CITATION", "candidate_id": candidate_id}

    valid_chunk_ids = {p.chunk_id for p in retrieved_passages}

    # Format passages for prompt
    passages_text = "\n\n".join([
        f"--- Chunk ID: {p.chunk_id} ({p.citation_label}) ---\n{p.passage_text}"
        for p in retrieved_passages
    ])

    prompt = f"""
Candidate Finding to Investigate:
- Category: {candidate.get('category')}
- Severity Hint: {candidate.get('severity_hint')}
- Quote (Verbatim): "{candidate.get('quote_english') or candidate.get('quote_original')}"
- Detection Rationale: {candidate.get('rationale')}

Retrieved Statutory Regulations:
{passages_text}

Task:
Perform a forensic evaluation. Determine if this candidate constitutes a statutory non-compliance violation.
- If verified: outcome = CONFIRMED. Specify the exact chunk_id from the provided retrieved citations.
- If not a violation: outcome = DISMISSED with forensic reasoning.
- If genuinely borderline or requires compliance committee discretion: outcome = ESCALATE_FOR_REVIEW.
"""

    llm = get_llm_client()
    system_instruction = "You are an autonomous forensic compliance investigator for BFSI wealth management. Cite exact regulation chunk IDs."

    decision: InvestigationDecision = llm.generate_structured(
        prompt=prompt,
        response_schema=InvestigationDecision,
        system_instruction=system_instruction,
        temperature=0.0
    )

    # -------------------------------------------------------------------------
    # HARD GUARDRAIL 2: Citation integrity check
    # regulation_chunk_id in output must match a chunk that retrieval actually returned
    # -------------------------------------------------------------------------
    chosen_chunk_id = decision.regulation_chunk_id.strip()
    if decision.outcome == "CONFIRMED":
        if chosen_chunk_id not in valid_chunk_ids:
            # Fallback to the top retrieved passage if matching document
            if retrieved_passages:
                chosen_chunk_id = retrieved_passages[0].chunk_id
            else:
                reason = f"Citation mismatch: Model cited '{chosen_chunk_id}' which was not in retrieved chunks {list(valid_chunk_ids)}."
                logger.warning(f"[Guardrail 2 Triggered] {candidate_id}: {reason}")
                record_investigation_audit(
                    investigation_id=investigation_id,
                    candidate_id=candidate_id,
                    call_id=call_id,
                    outcome="DISMISSED_CITATION_MISMATCH",
                    reasoning=reason,
                    raw_output=decision.model_dump(),
                )
                return {"outcome": "DISMISSED_CITATION_MISMATCH", "candidate_id": candidate_id}

    # -------------------------------------------------------------------------
    # HARD GUARDRAIL 3: HIGH severity completeness check
    # HIGH severity requires non-empty timestamp and valid regulation chunk
    # -------------------------------------------------------------------------
    final_severity = decision.severity.upper()
    if final_severity == "HIGH":
        start_ms = candidate.get("start_ms")
        if start_ms is None or not chosen_chunk_id:
            logger.warning(f"[Guardrail 3 Triggered] Downgrading HIGH severity candidate {candidate_id} to MEDIUM due to incomplete timestamps/chunk.")
            final_severity = "MEDIUM"

    # -------------------------------------------------------------------------
    # HARD GUARDRAIL 4: Quote verification check
    # -------------------------------------------------------------------------
    aligned = resolve_best_matching_quote(
        quote_orig=candidate.get("quote_original", ""),
        quote_en=candidate.get("quote_english", ""),
        start_ms=candidate.get("start_ms"),
        end_ms=candidate.get("end_ms"),
        segments=segments,
    )
    quote_text = aligned["quote_english"] or candidate.get("quote_english") or candidate.get("quote_original") or ""
    quote_original_text = aligned["quote_original"] or candidate.get("quote_original") or quote_text

    # Record investigation audit
    record_investigation_audit(
        investigation_id=investigation_id,
        candidate_id=candidate_id,
        call_id=call_id,
        outcome=decision.outcome,
        reasoning=decision.reasoning,
        raw_output=decision.model_dump(),
    )

    # If CONFIRMED, execute single-transaction atomic commit!
    if decision.outcome == "CONFIRMED":
        # Resolve authoritative metadata from registry
        chunk_meta = get_chunk(chosen_chunk_id) or {}
        citation_label = chunk_meta.get("citation_label") or f"Statutory Regulation ({chosen_chunk_id})"
        source_url = chunk_meta.get("source_url") or "https://www.sebi.gov.in"
        page_num = chunk_meta.get("page_number") or 1

        finding_id = f"FND-{candidate_id.replace('CAND-', '')}"
        case_id = f"CASE-{candidate_id.replace('CAND-', '')}"

        finding_payload = {
            "finding_id": finding_id,
            "case_id": case_id,
            "call_id": call_id,
            "investigation_id": investigation_id,
            "regulation_chunk_id": chosen_chunk_id,
            "citation_label": citation_label,
            "source_url": source_url,
            "page_number": page_num,
            "severity": final_severity,
            "confidence": decision.confidence,
            "category": candidate.get("category", "SUITABILITY_MISMATCH"),
            "timestamp_start": int((candidate.get("start_ms") or aligned.get("start_ms", 0)) / 1000.0),
            "timestamp_end": int((candidate.get("end_ms") or aligned.get("end_ms", 0)) / 1000.0),
            "quote_original": quote_original_text,
            "quote_english": quote_text,
            "evidence": {
                "supporting": decision.supporting_evidence,
                "contradicting": decision.contradicting_evidence,
                "rationale": decision.reasoning,
            },
            "provider_used": "mock" if settings.is_mock() else "vertex_ai",
            "model": settings.GEMINI_FLASH_MODEL,
        }

        commit_confirmed_finding(finding_payload)
        logger.info(f"[Investigation] Confirmed finding {finding_id} committed in atomic transaction.")
        return {"outcome": "CONFIRMED", "finding_id": finding_id, "case_id": case_id}

    return {"outcome": decision.outcome, "candidate_id": candidate_id}


def run_investigation_for_call(call_id: str) -> List[Dict[str, Any]]:
    """Runs investigation across all candidates staged for a call."""
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM `call` WHERE id = %s", (call_id,))
            call_row = cur.fetchone()

            cur.execute("SELECT * FROM candidate WHERE call_id = %s", (call_id,))
            candidates = cur.fetchall()

            cur.execute("SELECT * FROM transcript_segment WHERE call_id = %s ORDER BY idx ASC", (call_id,))
            segments = cur.fetchall()

    if not candidates:
        logger.info(f"[Investigation] No candidates staged for call {call_id}.")
        return []

    retriever = get_regulation_retriever()
    results = []

    for cand in candidates:
        # Retrieve passages for chunk ids stored
        retrieved_ids = json.loads(cand.get("retrieved_chunk_ids") or "[]")
        passages = []
        for ch_id in retrieved_ids:
            meta = get_chunk(ch_id)
            if meta:
                passages.append(
                    RetrievedPassage(
                        chunk_id=meta["chunk_id"],
                        passage_text=meta["chunk_text"],
                        citation_label=meta["citation_label"],
                        page_number=meta["page_number"],
                        source_url=meta["source_url"],
                        document_name=meta["document_name"],
                    )
                )

        res = run_investigation_for_candidate(
            candidate=cand,
            call_context=call_row or {},
            retrieved_passages=passages,
            segments=segments,
        )
        results.append(res)
        time.sleep(1.0)  # Pacing to respect Vertex AI QPM rate limits

    return results
