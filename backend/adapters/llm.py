"""
ARGUS — LLM Client Adapter (backend/adapters/llm.py)

Provides LLMClient interface:
- Live: gemini-3.5-flash via google-genai on Vertex AI with structured output
- Mock: Deterministic fixture generator aligned with the 10 call scripts & ground truth
"""

import re
import json
import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Type, TypeVar
from pydantic import BaseModel

from backend.core.config import settings

logger = logging.getLogger("argus.adapters.llm")

T = TypeVar("T", bound=BaseModel)


class LLMClient(ABC):
    """Abstract interface for LLM operations with structured schema output."""

    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        system_instruction: Optional[str] = None,
        temperature: float = 0.0,
    ) -> T:
        """Generates structured response validated against a Pydantic schema."""
        pass

    @abstractmethod
    def generate_chat(
        self,
        messages: List[Dict[str, str]],
        system_instruction: Optional[str] = None,
    ) -> str:
        """Generates free-text chat response for the conversational assistant."""
        pass


class MockLLMClient(LLMClient):
    """
    Mock LLM client that returns deterministic responses derived from call context,
    prompts, and ground-truth rules for the 10 demo calls.
    """

    def __init__(self):
        if not settings.is_mock():
            raise RuntimeError(
                f"ABSOLUTE RULE 1 VIOLATION: Mock adapter 'MockLLMClient' instantiated "
                f"while ARGUS_PROVIDER_MODE='{settings.PROVIDER_MODE}'. Mock usage is strictly prohibited in live mode!"
            )

    def generate_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        system_instruction: Optional[str] = None,
        temperature: float = 0.0,
    ) -> T:
        schema_name = response_schema.__name__

        # 1. Speaker Mapping & Translation Schema
        if "SpeakerMapping" in schema_name or "RoleMapping" in schema_name:
            sample_data = {
                "rm_speaker_label": "Speaker 1",
                "customer_speaker_label": "Speaker 2",
                "confidence": 0.98,
                "reasoning": "Speaker 1 initiates the conversation with RM greeting and product introduction.",
                "speaker_mapping_method": "llm",
                "translated_segments": []
            }
            return response_schema.model_validate(sample_data)

        # 2. Candidate Detection Schema
        if "DetectionOutput" in schema_name or "CandidateList" in schema_name or "Candidate" in schema_name:
            candidates = []
            prompt_lower = prompt.lower()

            # Clean / fully compliant calls produce 0 candidates
            if "RM002_CUST005" in prompt or "RM004_CUST004" in prompt or "RM005_CUST001" in prompt:
                return response_schema.model_validate({"candidates": []})

            # Call 1: RM001_CUST001 - Suitability Mismatch (HIGH)
            if "RM001_CUST001" in prompt:
                candidates.append({
                    "candidate_id": "CAND-001",
                    "category": "SUITABILITY_MISMATCH",
                    "severity_hint": "HIGH",
                    "start_ms": 29000,
                    "end_ms": 39000,
                    "speaker": "RM",
                    "quote_original": "I really think you should put at least two lakhs into this.",
                    "quote_english": "I really think you should put at least two lakhs into this.",
                    "rationale": "High-risk small cap equity fund recommended to a Conservative investor.",
                    "regulation_queries": ["suitability assessment customer risk profile SEBI", "Code of Conduct suitability"]
                })

            # Call 2: RM001_CUST004 - Guaranteed Return (MEDIUM, mild/implied)
            elif "RM001_CUST004" in prompt:
                candidates.append({
                    "candidate_id": "CAND-001",
                    "category": "GUARANTEED_RETURN",
                    "severity_hint": "MEDIUM",
                    "start_ms": 21000,
                    "end_ms": 32000,
                    "speaker": "RM",
                    "quote_original": "loss hone ka koi",
                    "quote_english": "there is no chance of loss, the returns are practically assured",
                    "rationale": "RM uses soft but clear return-assurance language minimizing market risk.",
                    "regulation_queries": ["guaranteed return", "assured returns mutual funds SEBI"]
                })

            # Call 3: RM002_CUST002 - Guaranteed Return (HIGH, explicit 15%)
            elif "RM002_CUST002" in prompt:
                candidates.append({
                    "candidate_id": "CAND-001",
                    "category": "GUARANTEED_RETURN",
                    "severity_hint": "HIGH",
                    "start_ms": 21000,
                    "end_ms": 35000,
                    "speaker": "RM",
                    "quote_original": "15%",
                    "quote_english": "guaranteed 15% return on investment",
                    "rationale": "RM makes an explicit, unambiguous guaranteed-return claim of 15%.",
                    "regulation_queries": ["guaranteed returns prohibition SEBI AMFI", "prohibition of assured return schemes"]
                })

            # Call 5: RM003_CUST003_20260212 - Missing Risk Disclosure (HIGH)
            elif "RM003_CUST003_20260212" in prompt or ("RM003_CUST003" in prompt and "thematic" in prompt_lower):
                candidates.append({
                    "candidate_id": "CAND-001",
                    "category": "MISSING_RISK_DISCLOSURE",
                    "severity_hint": "HIGH",
                    "start_ms": 10000,
                    "end_ms": 25000,
                    "speaker": "RM",
                    "quote_original": "No specific risk disclosures given.",
                    "quote_english": "No specific risk disclosures given.",
                    "rationale": "Mandatory risk-o-meter and sector concentration disclosures omitted on thematic fund.",
                    "regulation_queries": ["mandatory risk-o-meter disclosure circular SEBI", "scheme related documents risk factors"]
                })

            # Call 6: RM003_CUST003_20260630 - Ambiguous / Hedged Return Claim (LOW)
            elif "RM003_CUST003_20260630" in prompt or ("RM003_CUST003" in prompt and "multi asset" in prompt_lower):
                candidates.append({
                    "candidate_id": "CAND-001",
                    "category": "GUARANTEED_RETURN",
                    "severity_hint": "LOW",
                    "start_ms": 12000,
                    "end_ms": 24000,
                    "speaker": "RM",
                    "quote_original": "I think this should perform well over the next year or so.",
                    "quote_english": "I think this should perform well over the next year or so.",
                    "rationale": "Soft opinion-based return claim. Evaluated as low severity borderline claim.",
                    "regulation_queries": ["indicative return performance claim AMFI code"]
                })

            # Call 8: RM004_CUST002 - Missing Risk Disclosure (MEDIUM)
            elif "RM004_CUST002" in prompt:
                candidates.append({
                    "candidate_id": "CAND-001",
                    "category": "MISSING_RISK_DISCLOSURE",
                    "severity_hint": "MEDIUM",
                    "start_ms": 31000,
                    "end_ms": 42000,
                    "speaker": "RM",
                    "quote_original": "market risk",
                    "quote_english": "obviously there is market risk, but overall this is less risky than equity-only funds",
                    "rationale": "Vague and partial disclosure of market risk without statutory disclaimer.",
                    "regulation_queries": ["risk disclosure requirements mutual funds distributor", "SEBI circular disclosure standards"]
                })

            # Call 9: RM005_CUST005 - Ambiguous Suitability (LOW)
            elif "RM005_CUST005" in prompt:
                candidates.append({
                    "candidate_id": "CAND-001",
                    "category": "SUITABILITY_MISMATCH",
                    "severity_hint": "LOW",
                    "start_ms": 15000,
                    "end_ms": 28000,
                    "speaker": "RM",
                    "quote_original": "This fund should suit your medium-term horizon.",
                    "quote_english": "This fund should suit your medium-term horizon.",
                    "rationale": "Product technically matches Moderate profile but customer has Low experience.",
                    "regulation_queries": ["suitability assessment investment experience SEBI AMFI", "distributor code of conduct suitability"]
                })
            else:
                candidates.append({
                    "candidate_id": "CAND-001",
                    "category": "GUARANTEED_RETURN",
                    "severity_hint": "MEDIUM",
                    "start_ms": 10000,
                    "end_ms": 20000,
                    "speaker": "RM",
                    "quote_original": "guaranteed returns",
                    "quote_english": "guaranteed returns",
                    "rationale": "General candidate flagged.",
                    "regulation_queries": ["guaranteed return SEBI"]
                })

            sample_data = {"candidates": candidates}
            return response_schema.model_validate(sample_data)

        # 3. Investigation Decision Schema
        if "InvestigationDecision" in schema_name or "InvestigationOutcome" in schema_name:
            prompt_lower = prompt.lower()
            chunk_matches = re.findall(r"Chunk ID:\s*([A-Za-z0-9_\-]+)", prompt)
            chosen_chunk = chunk_matches[0] if chunk_matches else "SEBI_MF_2026_REG_39"

            if "clean" in prompt_lower or "compliant" in prompt_lower or "RM002_CUST005" in prompt or "RM004_CUST004" in prompt or "RM005_CUST001" in prompt:
                sample_data = {
                    "outcome": "DISMISSED",
                    "severity": "LOW",
                    "confidence": 0.95,
                    "regulation_chunk_id": "",
                    "reasoning": "Full statutory disclosures provided; call adheres to SEBI Code of Conduct.",
                    "supporting_evidence": ["Customer risk profile confirmed", "Disclosures made"],
                    "contradicting_evidence": []
                }
            elif "RM005_CUST005" in prompt:
                sample_data = {
                    "outcome": "CONFIRMED",
                    "severity": "LOW",
                    "confidence": 0.76,
                    "regulation_chunk_id": chosen_chunk,
                    "reasoning": "Borderline suitability concern regarding customer investment experience. Confirmed at LOW severity.",
                    "supporting_evidence": ["Customer has Low investment experience"],
                    "contradicting_evidence": ["Product risk rating matches Moderate risk profile"]
                }
            elif "RM003_CUST003_20260630" in prompt:
                sample_data = {
                    "outcome": "CONFIRMED",
                    "severity": "LOW",
                    "confidence": 0.78,
                    "regulation_chunk_id": chosen_chunk,
                    "reasoning": "Hedged, opinion-based return claim ('should perform well'). Evaluated at LOW severity.",
                    "supporting_evidence": ["Soft return expectation communicated without disclaimer"],
                    "contradicting_evidence": ["No explicit numeric guarantee"]
                }
            elif "RM001_CUST004" in prompt:
                sample_data = {
                    "outcome": "CONFIRMED",
                    "severity": "MEDIUM",
                    "confidence": 0.88,
                    "regulation_chunk_id": chosen_chunk,
                    "reasoning": "Implied return-assurance language ('loss hone ka koi chance nahi') violates AMFI Code of Conduct.",
                    "supporting_evidence": ["Verbatim quote minimizes capital loss risk"],
                    "contradicting_evidence": []
                }
            elif "RM004_CUST002" in prompt:
                sample_data = {
                    "outcome": "CONFIRMED",
                    "severity": "MEDIUM",
                    "confidence": 0.86,
                    "regulation_chunk_id": chosen_chunk,
                    "reasoning": "Partial and inadequate disclosure given regarding hybrid fund risks.",
                    "supporting_evidence": ["Mandatory risk-o-meter explanation omitted"],
                    "contradicting_evidence": []
                }
            elif "RM002_CUST002" in prompt:
                sample_data = {
                    "outcome": "CONFIRMED",
                    "severity": "HIGH",
                    "confidence": 0.98,
                    "regulation_chunk_id": chosen_chunk,
                    "reasoning": "Explicit, unambiguous guaranteed-return claim (15%) on equity product directly violates AMFI §II.4.g.",
                    "supporting_evidence": ["15% return assurance given in recording"],
                    "contradicting_evidence": []
                }
            elif "RM003_CUST003_20260212" in prompt:
                sample_data = {
                    "outcome": "CONFIRMED",
                    "severity": "HIGH",
                    "confidence": 0.94,
                    "regulation_chunk_id": chosen_chunk,
                    "reasoning": "Total omission of mandatory risk-o-meter and concentration disclosures on high-risk thematic fund.",
                    "supporting_evidence": ["SEBI Master Circular requirement violated"],
                    "contradicting_evidence": []
                }
            elif "RM001_CUST001" in prompt:
                sample_data = {
                    "outcome": "CONFIRMED",
                    "severity": "HIGH",
                    "confidence": 0.96,
                    "regulation_chunk_id": chosen_chunk,
                    "reasoning": "Severe suitability mismatch: High-risk small cap equity fund recommended to Conservative customer.",
                    "supporting_evidence": ["Customer risk profile is Conservative", "Product risk class is High"],
                    "contradicting_evidence": []
                }
            else:
                sample_data = {
                    "outcome": "CONFIRMED",
                    "severity": "HIGH" if "high" in prompt_lower else "MEDIUM",
                    "confidence": 0.90,
                    "regulation_chunk_id": chosen_chunk,
                    "reasoning": "Forensic evaluation confirms regulatory non-compliance with statutory guidelines.",
                    "supporting_evidence": ["Transcript evidence confirms breach"],
                    "contradicting_evidence": []
                }
            return response_schema.model_validate(sample_data)

        # Generic fallback
        return response_schema.model_validate({})

    def generate_chat(
        self,
        messages: List[Dict[str, str]],
        system_instruction: Optional[str] = None,
    ) -> str:
        last_msg = messages[-1]["content"] if messages else ""
        return (
            f"[ARGUS Mock Assistant] Analyzed your query regarding '{last_msg[:40]}...'. "
            f"Based on grounded surveillance data, Relationship Manager calls have been reviewed against SEBI/AMFI statutory regulations."
        )


class VertexGeminiClient(LLMClient):
    """
    Live LLM client using gemini-3.5-flash / gemini-2.5-flash on Vertex AI.
    """

    def __init__(self, model_id: Optional[str] = None):
        self.model_id = model_id or settings.GEMINI_FLASH_MODEL
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from google import genai
                # =========================================================================
                # PREVIOUS: Gemini 2.5 Flash on Vertex AI (Commented Out)
                # =========================================================================
                # self._client = genai.Client(
                #     vertexai=True,
                #     project=settings.PROJECT_ID,
                #     location=settings.VERTEX_LOCATION,  # us-central1
                # )

                # =========================================================================
                # CURRENT: Gemini 3.5 Flash on Vertex AI (location="global")
                # (For gemini-2.5-flash speaker role mapping, us-central1 or global works)
                # =========================================================================
                loc = "global" if "3.5" in self.model_id else settings.VERTEX_LOCATION
                try:
                    self._client = genai.Client(
                        enterprise=True,
                        project=settings.PROJECT_ID,
                        location=loc,
                    )
                except TypeError:
                    self._client = genai.Client(
                        vertexai=True,
                        project=settings.PROJECT_ID,
                        location=loc,
                    )
            except Exception as exc:
                raise RuntimeError(f"VertexGeminiClient requires google-genai and ADC credentials: {exc}")
        return self._client

    def generate_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        system_instruction: Optional[str] = None,
        temperature: float = 0.0,
    ) -> T:
        client = self._get_client()
        from google.genai import types

        config = types.GenerateContentConfig(
            temperature=temperature,
            response_mime_type="application/json",
            response_schema=response_schema,
            system_instruction=system_instruction,
        )

        max_retries = 3
        backoff = 2.0
        response = None
        for attempt in range(1, max_retries + 1):
            try:
                response = client.models.generate_content(
                    model=self.model_id,
                    contents=prompt,
                    config=config,
                )
                break
            except Exception as exc:
                err_str = str(exc)
                if ("429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "503" in err_str or "UNAVAILABLE" in err_str or "Deadline" in err_str) and attempt < max_retries:
                    logger.warning(f"[Retry {attempt}/{max_retries}] Transient Vertex AI error: {exc}. Retrying in {backoff}s...")
                    time.sleep(backoff)
                    backoff *= 2.0
                else:
                    raise

        text = response.text.strip()
        # Clean any surrounding markdown block if returned
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return response_schema.model_validate_json(text.strip())

    def generate_chat(
        self,
        messages: List[Dict[str, str]],
        system_instruction: Optional[str] = None,
    ) -> str:
        client = self._get_client()
        from google.genai import types

        contents = []
        for m in messages:
            role = "user" if m.get("role") in ("user", "human") else "model"
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=m.get("content", ""))]
                )
            )

        config = types.GenerateContentConfig(
            temperature=0.2,
            system_instruction=system_instruction,
        )

        max_retries = 3
        backoff = 2.0
        response = None
        for attempt in range(1, max_retries + 1):
            try:
                response = client.models.generate_content(
                    model=self.model_id,
                    contents=contents,
                    config=config,
                )
                break
            except Exception as exc:
                err_str = str(exc)
                if ("429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "503" in err_str or "UNAVAILABLE" in err_str or "Deadline" in err_str) and attempt < max_retries:
                    logger.warning(f"[Retry {attempt}/{max_retries}] Transient Vertex AI error: {exc}. Retrying in {backoff}s...")
                    time.sleep(backoff)
                    backoff *= 2.0
                else:
                    raise

        return response.text or ""


def get_llm_client(model_id: Optional[str] = None) -> LLMClient:
    """Factory creating LLMClient based on ARGUS_PROVIDER_MODE."""
    if settings.is_mock():
        return MockLLMClient()
    return VertexGeminiClient(model_id=model_id or settings.GEMINI_FLASH_MODEL)
