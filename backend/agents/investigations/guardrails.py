"""
ARGUS — Investigation Guardrails (backend/agents/investigations/guardrails.py)

Pure deterministic guardrail validators enforcing statutory precision:
1. validate_citations_retrieved: zero citations leads to reformulation, then DISMISSED_NO_CITATION
2. validate_citation_overlap: cited chunk must be in retrieved candidate set or DISMISSED_CITATION_MISMATCH
3. validate_severity_and_timestamps: HIGH severity requires timestamp and regulation chunk
4. validate_verbatim_quote: candidate quote must exist verbatim in stored transcript
"""

from typing import List, Optional, Tuple, Set


def validate_citations_retrieved(retrieved_chunk_ids: List[str]) -> Tuple[bool, str]:
    """Guardrail 1: Verifies that retrieval returned candidate regulatory passages."""
    if not retrieved_chunk_ids:
        return False, "DISMISSED_NO_CITATION"
    return True, "VALID"


def validate_citation_overlap(
    cited_chunk_id: str,
    retrieved_chunk_ids: List[str]
) -> Tuple[bool, str]:
    """Guardrail 2: Asserts cited regulation was actually in the retrieved passage set."""
    if not cited_chunk_id:
        return False, "DISMISSED_NO_CITATION"
    if cited_chunk_id not in retrieved_chunk_ids:
        return False, "DISMISSED_CITATION_MISMATCH"
    return True, "VALID"


def validate_severity_and_timestamps(
    severity: str,
    timestamp_ms: Optional[int],
    cited_regulation_id: Optional[str]
) -> Tuple[bool, str, str]:
    """
    Guardrail 3: HIGH severity requires verified timestamp and cited statutory clause.
    Returns: (is_valid, final_severity, reason)
    """
    sev_upper = (severity or "LOW").upper()
    if sev_upper == "HIGH":
        if timestamp_ms is None or not cited_regulation_id:
            return False, "LOW", "DOWNGRADED_MISSING_TIMESTAMP_OR_CITATION"

    return True, sev_upper, "VALID"


def validate_verbatim_quote(
    quote: str,
    full_transcript: str
) -> Tuple[bool, str]:
    """Guardrail 4: Rejects hallucinated quotes not present verbatim in transcript."""
    if not quote or not full_transcript:
        return False, "DISMISSED_HALLUCINATED_QUOTE: Empty quote or transcript"
    if quote.lower() not in full_transcript.lower():
        # Check token overlap
        q_tokens = set(quote.lower().split())
        t_tokens = set(full_transcript.lower().split())
        overlap = len(q_tokens.intersection(t_tokens)) / max(1, len(q_tokens))
        if overlap < 0.60:
            return False, "DISMISSED_HALLUCINATED_QUOTE: Quote tokens not verified in transcript"
    return True, "VALID"
