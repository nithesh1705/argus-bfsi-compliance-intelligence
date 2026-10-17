"""
ARGUS — Distributed Tracing (backend/observability/trace.py)

Instruments pipeline stages and HTTP requests using OpenTelemetry:
- Live: Google Cloud Trace Exporter (opentelemetry-exporter-gcp-trace)
- Mock: Console/In-memory trace span exporter
- Enforces strict security: Zero PII in span attributes (IDs, counts, durations only).
"""

import os
import logging
from contextlib import contextmanager
from typing import Dict, Any, Optional, Generator

from backend.core.config import settings

logger = logging.getLogger("argus.observability.trace")

# Safe allow-list of attribute keys (PII is strictly excluded)
ALLOWED_ATTRIBUTE_KEYS = {
    "call_id",
    "stage",
    "model",
    "token_count_prompt",
    "token_count_completion",
    "segment_count",
    "candidate_count",
    "outcome",
    "status",
    "duration_ms",
    "provider_used",
    "run_id",
    "is_mock",
}


class MockSpan:
    """In-memory trace span for offline execution and mock mode."""

    def __init__(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        self.name = name
        self.attributes = {}
        if attributes:
            self.set_attributes(attributes)

    def set_attribute(self, key: str, value: Any):
        if key in ALLOWED_ATTRIBUTE_KEYS:
            self.attributes[key] = value

    def set_attributes(self, attrs: Dict[str, Any]):
        for k, v in attrs.items():
            self.set_attribute(k, v)


_tracer_initialized = False

def _init_tracer():
    global _tracer_initialized
    if _tracer_initialized or settings.is_mock() or not settings.TRACE_ENABLED:
        return
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.gcp_trace import CloudTraceSpanExporter

        provider = TracerProvider()
        processor = BatchSpanProcessor(CloudTraceSpanExporter(project_id=settings.PROJECT_ID))
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
        _tracer_initialized = True
        logger.info(f"OpenTelemetry CloudTraceSpanExporter initialized for project '{settings.PROJECT_ID}'")
    except Exception as exc:
        logger.warning(f"Could not initialize OpenTelemetry CloudTraceSpanExporter: {exc}")
        _tracer_initialized = True


@contextmanager
def TraceSpan(name: str, attributes: Optional[Dict[str, Any]] = None) -> Generator[MockSpan, None, None]:
    """
    Context manager creating an OpenTelemetry trace span.
    Exports to Cloud Trace in live mode or logs to memory in mock mode.
    """
    span = MockSpan(name, attributes)

    if not settings.is_mock() and settings.TRACE_ENABLED:
        _init_tracer()
        try:
            from opentelemetry import trace
            tracer = trace.get_tracer("argus.pipeline")
            with tracer.start_as_current_span(name) as live_span:
                if attributes:
                    for k, v in attributes.items():
                        if k in ALLOWED_ATTRIBUTE_KEYS:
                            live_span.set_attribute(k, v)
                yield live_span
                return
        except Exception as exc:
            logger.warning(f"Live trace export failed: {exc}")

    # Fallback / Mock execution
    yield span
