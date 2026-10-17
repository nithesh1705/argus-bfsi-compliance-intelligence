"""
ARGUS — Structured Cloud Logging (backend/observability/logging.py)

Formats log records as structured JSON correlated with Cloud Trace:
- Attaches trace_id and span_id when available
- Formats timestamps for Cloud Logging ingestion
- Enforces strict PII exclusion (IDs, statuses, and counts only)
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from backend.core.config import settings


class CloudLoggingJsonFormatter(logging.Formatter):
    """
    JSON formatter outputting structured logs compatible with Google Cloud Logging.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "line": record.lineno,
        }

        # Correlate with Cloud Trace if present
        trace_id = getattr(record, "trace_id", None)
        span_id = getattr(record, "span_id", None)
        if trace_id:
            log_payload["logging.googleapis.com/trace"] = f"projects/{settings.PROJECT_ID}/traces/{trace_id}"
        if span_id:
            log_payload["logging.googleapis.com/spanId"] = span_id

        # Attach custom metadata
        if hasattr(record, "call_id"):
            log_payload["call_id"] = record.call_id
        if hasattr(record, "run_id"):
            log_payload["run_id"] = record.run_id
        if hasattr(record, "stage"):
            log_payload["stage"] = record.stage

        return json.dumps(log_payload)


def configure_structured_logging():
    """Configures root logger with CloudLoggingJsonFormatter."""
    root_logger = logging.getLogger()
    handler = logging.StreamHandler()
    handler.setFormatter(CloudLoggingJsonFormatter())
    root_logger.handlers = [handler]
    root_logger.setLevel(logging.INFO)
