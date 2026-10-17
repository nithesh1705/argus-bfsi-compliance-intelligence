"""
ARGUS — Sensitive Data Protection / PII Redactor Adapter (backend/adapters/pii_redactor.py)

Redacts PII (PAN, Aadhaar, Phone, Email, Card numbers) before transcript text
is saved to Cloud SQL or evaluated by Gemini Detection/Investigation.
Preserves segment boundaries and audio timestamps.
"""

import re
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from backend.core.config import settings

logger = logging.getLogger("argus.adapters.dlp")


class PiiRedactionResult:
    def __init__(self, redacted_text: str, findings_count: int, info_types_detected: List[str]):
        self.redacted_text = redacted_text
        self.findings_count = findings_count
        self.info_types_detected = info_types_detected


class PiiRedactor(ABC):
    """Abstract interface for PII redaction."""

    @abstractmethod
    def redact_text(self, text: str) -> PiiRedactionResult:
        """Redact sensitive PII tokens from input text."""
        pass


class RegexPiiRedactor(PiiRedactor):
    """
    Mock implementation of PII redaction using deterministic regex matching
    for Indian statutory PII entities.
    """

    def __init__(self):
        if not settings.is_mock():
            raise RuntimeError(
                f"ABSOLUTE RULE 1 VIOLATION: Mock adapter 'RegexPiiRedactor' instantiated "
                f"while ARGUS_PROVIDER_MODE='{settings.PROVIDER_MODE}'. Mock usage is strictly prohibited in live mode!"
            )

    # Indian PAN: 5 uppercase letters, 4 digits, 1 uppercase letter
    PAN_REGEX = re.compile(r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b', re.IGNORECASE)

    # Indian Aadhaar: 12 digits (often grouped in 4s with optional spaces or dashes)
    AADHAAR_REGEX = re.compile(r'\b[2-9]{1}[0-9]{3}[-\s]?[0-9]{4}[-\s]?[0-9]{4}\b')

    # Phone: 10-digit Indian mobile numbers (+91 optional)
    PHONE_REGEX = re.compile(r'(?:\+91[\-\s]?)?[6-9]\d{9}\b')

    # Email address
    EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b')

    # Payment Card (Visa, MasterCard, RuPay 13-16 digits)
    CARD_REGEX = re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b|\b\d{16}\b')

    def redact_text(self, text: str) -> PiiRedactionResult:
        if not text:
            return PiiRedactionResult(text, 0, [])

        redacted = text
        detected_types = []
        count = 0

        # PAN
        pan_matches = self.PAN_REGEX.findall(redacted)
        if pan_matches:
            redacted = self.PAN_REGEX.sub("[PAN]", redacted)
            detected_types.append("INDIA_PAN_NUMBER")
            count += len(pan_matches)

        # Aadhaar
        aadhaar_matches = self.AADHAAR_REGEX.findall(redacted)
        if aadhaar_matches:
            redacted = self.AADHAAR_REGEX.sub("[AADHAAR]", redacted)
            detected_types.append("INDIA_AADHAAR_NUMBER")
            count += len(aadhaar_matches)

        # Payment card
        card_matches = self.CARD_REGEX.findall(redacted)
        if card_matches:
            redacted = self.CARD_REGEX.sub("[CARD]", redacted)
            detected_types.append("CREDIT_CARD_NUMBER")
            count += len(card_matches)

        # Phone
        phone_matches = self.PHONE_REGEX.findall(redacted)
        if phone_matches:
            redacted = self.PHONE_REGEX.sub("[PHONE]", redacted)
            detected_types.append("PHONE_NUMBER")
            count += len(phone_matches)

        # Email
        email_matches = self.EMAIL_REGEX.findall(redacted)
        if email_matches:
            redacted = self.EMAIL_REGEX.sub("[EMAIL]", redacted)
            detected_types.append("EMAIL_ADDRESS")
            count += len(email_matches)

        return PiiRedactionResult(
            redacted_text=redacted,
            findings_count=count,
            info_types_detected=list(set(detected_types))
        )


class SensitiveDataProtectionRedactor(PiiRedactor):
    """
    Live implementation using Google Cloud Sensitive Data Protection (DLP API).
    """

    def __init__(self, project_id: Optional[str] = None):
        self.project_id = project_id or settings.PROJECT_ID
        self._client = None

    def _get_client(self):
        # TODO(PHASE2-VERIFY): Confirm DLP API credentials and Indian info types availability in target region
        if self._client is None:
            try:
                from google.cloud import dlp_v2
                self._client = dlp_v2.DlpServiceClient()
            except Exception as exc:
                raise RuntimeError(f"SensitiveDataProtectionRedactor requires google-cloud-dlp: {exc}")
        return self._client

    def redact_text(self, text: str) -> PiiRedactionResult:
        if not text:
            return PiiRedactionResult(text, 0, [])

        client = self._get_client()
        parent = f"projects/{self.project_id}"

        # Info types to inspect and de-identify (verified against Google Cloud DLP catalog)
        info_types = [
            {"name": "INDIA_PAN_INDIVIDUAL"},
            {"name": "INDIA_AADHAAR_INDIVIDUAL"},
            {"name": "PHONE_NUMBER"},
            {"name": "EMAIL_ADDRESS"},
            {"name": "CREDIT_CARD_NUMBER"},
        ]

        custom_info_types = [
            {
                "info_type": {"name": "INDIA_PAN_CUSTOM"},
                "regex": {"pattern": r"[A-Z]{5}[0-9]{4}[A-Z]{1}"}
            },
            {
                "info_type": {"name": "INDIA_AADHAAR_CUSTOM"},
                "regex": {"pattern": r"\b[2-9]{1}[0-9]{3}[-\s]?[0-9]{4}[-\s]?[0-9]{4}\b"}
            },
            {
                "info_type": {"name": "CREDIT_CARD_CUSTOM"},
                "regex": {"pattern": r"\b(?:\d{4}[-\s]?){3}\d{4}\b|\b\d{13,19}\b"}
            }
        ]

        item = {"value": text}
        inspect_config = {
            "info_types": info_types,
            "custom_info_types": custom_info_types,
            "min_likelihood": "POSSIBLE",
        }

        # Replace each info_type with its bracketed token: [PAN], [AADHAAR], etc.
        try:
            deidentify_config = {
                "info_type_transformations": {
                    "transformations": [
                        {
                            "primitive_transformation": {
                                "replace_with_info_type_config": {}
                            }
                        }
                    ]
                }
            }

            response = client.deidentify_content(
                request={
                    "parent": parent,
                    "deidentify_config": deidentify_config,
                    "inspect_config": inspect_config,
                    "item": item,
                }
            )

            redacted_val = response.item.value
            # Normalize Google DLP default format "[INDIA_PAN_NUMBER]" to standard tokens "[PAN]"
            redacted_val = (redacted_val
                            .replace("[INDIA_PAN_INDIVIDUAL]", "[PAN]")
                            .replace("[INDIA_PAN_CUSTOM]", "[PAN]")
                            .replace("[INDIA_AADHAAR_INDIVIDUAL]", "[AADHAAR]")
                            .replace("[INDIA_AADHAAR_CUSTOM]", "[AADHAAR]")
                            .replace("[CREDIT_CARD_NUMBER]", "[CARD]")
                            .replace("[CREDIT_CARD_CUSTOM]", "[CARD]")
                            .replace("[PHONE_NUMBER]", "[PHONE]")
                            .replace("[EMAIL_ADDRESS]", "[EMAIL]"))


            count_matches = len(re.findall(r'\[(PAN|AADHAAR|PHONE|EMAIL|CARD)\]', redacted_val))
            detected_types = list({f"INDIA_{m}" if m in ("PAN", "AADHAAR") else m for m in re.findall(r'\[(PAN|AADHAAR|PHONE|EMAIL|CARD)\]', redacted_val)})

            return PiiRedactionResult(
                redacted_text=redacted_val,
                findings_count=max(1, count_matches),
                info_types_detected=detected_types or [it["name"] for it in info_types]
            )

        except Exception as exc:
            logger.error(f"Live DLP deidentify_content failed: {exc}")
            raise


def get_pii_redactor() -> PiiRedactor:
    """Factory creating PiiRedactor based on ARGUS_PROVIDER_MODE and flags."""
    if not settings.DLP_ENABLED:
        class NoopRedactor(PiiRedactor):
            def redact_text(self, text: str):
                return PiiRedactionResult(text, 0, [])
        return NoopRedactor()

    if settings.is_mock():
        return RegexPiiRedactor()
    return SensitiveDataProtectionRedactor()
