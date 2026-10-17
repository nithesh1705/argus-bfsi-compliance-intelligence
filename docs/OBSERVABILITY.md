# ARGUS — Observability, Tracing & System Health

Architecture and operational guide for distributed tracing with Google Cloud Trace, structured logging with Cloud Logging, and the hybrid health panel.

[Back to documentation index](./INDEX.md) | [Next: Security & Governance](./SECURITY.md)

---

## Table of Contents

- [Observability Architecture](#observability-architecture)
- [Distributed Tracing with Google Cloud Trace](#distributed-tracing-with-google-cloud-trace)
  - [Pipeline Span Hierarchy](#pipeline-span-hierarchy)
  - [Zero-PII Trace Attribute Allow-List](#zero-pii-trace-attribute-allow-list)
  - [Cloud Trace Deep Linking](#cloud-trace-deep-linking)
- [Structured Logging & Trace Correlation](#structured-logging--trace-correlation)
- [The Hybrid Health Panel](#the-hybrid-health-panel)
  - [Live Probes vs Last-Known Statuses](#live-probes-vs-last-known-statuses)
  - [Provider Health State Table](#provider-health-state-table)
- [Observing ARGUS in Google Cloud Console](#observing-argus-in-google-cloud-console)
- [Related Documents](#related-documents)

---

## Observability Architecture

ARGUS treats observability as a first-class compliance requirement. Financial compliance platforms must account for every algorithmic decision, stage latency, and error event without leaking protected investor data into telemetry systems:

```
[Incoming Audio Finalize]
           │
           ▼
[argus.pipeline.run] ──── Span Trace ID: trace-9334633f51684c21
     │
     ├─► [ingestion.transcribe_and_redact]  (Mean: 64.0s)
     ├─► [detection.run]                   (Mean: 29.7s)
     ├─► [retrieval.search]                (Mean: 0.8s)
     ├─► [investigation.run]               (Mean: 66.3s)
     └─► [archive.move]                    (Mean: 2.4s)
           │
           ├─► Exported to Google Cloud Trace Explorer
           └─► Correlated with Google Cloud Logging JSON logs
```

Source implementations:
- Trace Context Manager: [`../backend/observability/trace.py`](../backend/observability/trace.py)
- Logging Formatter: [`../backend/observability/logging.py`](../backend/observability/logging.py)
- Observability API: [`../backend/api/routes/observability.py`](../backend/api/routes/observability.py)

---

## Distributed Tracing with Google Cloud Trace

The platform instruments all pipeline executions using OpenTelemetry (`opentelemetry-api`, `opentelemetry-sdk`, and `opentelemetry-exporter-gcp-trace`).

### Pipeline Span Hierarchy

When a recording is processed, a root span is created alongside nested child spans corresponding to constituent pipeline stages:

| Span Name | Type | Description | Key Tagged Attributes |
|---|---|---|---|
| `argus.pipeline.run` | Root Span | Total end-to-end call processing lifecycle | `call_id`, `run_id`, `status`, `duration_ms` |
| `ingestion.transcribe_and_redact` | Child Span | Audio transcription, translation, and DLP redaction | `call_id`, `segment_count`, `duration_ms` |
| `detection.run` | Child Span | Pre-screening and candidate staging | `call_id`, `candidate_count`, `model` |
| `retrieval.search` | Child Span | Grounding chunk search over regulation registry | `call_id`, `query`, `duration_ms` |
| `investigation.run` | Child Span | Forensic legal reasoning and guardrail checks | `call_id`, `outcome`, `token_count_prompt`, `token_count_completion` |
| `archive.move` | Child Span | Audio transfer from `incoming/` to `archive/` | `call_id`, `duration_ms` |

### Zero-PII Trace Attribute Allow-List
To guarantee that investor PII (PAN numbers, Aadhaar numbers, phone numbers, customer names) never leaks into distributed telemetry collectors, [`../backend/observability/trace.py`](../backend/observability/trace.py) enforces a strict attribute key allow-list:

```python
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
```

Any attribute key outside this explicit set is rejected before spans are dispatched to Cloud Trace.

### Cloud Trace Deep Linking
Every pipeline run generates an immutable `trace_id` saved in the `pipeline_run` database table. The backend formats direct deep links using the configured template:

```
https://console.cloud.google.com/traces/explorer?project=<YOUR_GCP_PROJECT_ID>&tid={trace_id}
```

Audit officers can click this deep link directly from the case view or system telemetry dashboard to inspect the distributed trace waterfall in the Google Cloud Console.

---

## Structured Logging & Trace Correlation

All backend application logs are emitted as structured JSON objects:

```json
{
  "timestamp": "2026-10-15T07:05:22.412Z",
  "severity": "INFO",
  "logger": "argus.agents.investigation",
  "message": "[Investigation] Confirmed finding FND-001 committed in atomic transaction.",
  "trace_id": "trace-9334633f51684c21",
  "call_id": "CALL_RM004_CUST004_20260228_1050",
  "run_id": "RUN-06674f7b4881"
}
```

By tagging every log entry with `trace_id` and `call_id`, Google Cloud Logs Explorer automatically links log streams to their corresponding Cloud Trace spans, allowing one-click transitions from error logs to the distributed execution waterfall.

---

## The Hybrid Health Panel

Exposed via `GET /api/system/health` and rendered in the Settings page, the health panel balances real-time accuracy with zero artificial operational latency:

### Live Probes vs Last-Known Statuses

| Dependency | Inspection Strategy | Frequency | Why Chosen |
|---|---|---|---|
| **Cloud SQL for MySQL** | **Live In-Process Check** (`SELECT 1`) | Every health check request | Lightweight (< 5ms), verifies database connection pool health directly. |
| **Cloud Storage** | **Live In-Process Check** (`list_objects`) | Every health check request | Instant metadata check verifying bucket accessibility. |
| **Vertex AI (Gemini Flash)** | **Last-Known Status** (read from `provider_health`) | Background update from actual runs | Pinging LLM endpoints on every health check would incur continuous API billing, exhaust rate quotas, and add 500ms artificial latency. |
| **Sensitive Data Protection (DLP)** | **Last-Known Status** (read from `provider_health`) | Background update from actual runs | Zero ping cost; health is derived from recent redaction operations. |
| **File Search Store** | **Last-Known Status** (read from `provider_health`) | Background update from actual runs | Validated against recent retrieval queries. |

### Provider Health State Table
The `provider_health` table maintains background operational status:

```sql
SELECT dependency_name, status, latency_ms, last_checked_at FROM provider_health;
```

---

## Observing ARGUS in Google Cloud Console

1. **Viewing Distributed Traces:**
   - In Google Cloud Console, navigate to **Trace > Trace Explorer**.
   - Filter by span name (e.g. `Root: argus.pipeline.run` or `investigation.run`).
   - Click a trace waterfall to examine stage timings, token prompt counts, and completion durations.
2. **Viewing Structured Logs:**
   - Navigate to **Logging > Logs Explorer**.
   - Query by resource: `resource.type="cloud_run_revision" AND resource.labels.service_name="argus-backend"`.
   - Filter for specific calls using `jsonPayload.call_id="CALL_RM001_CUST001_20260310_1030"`.
3. **Observing Latencies in ARGUS UI:**
   - Navigate to the **Observability** page (`/observability`) in the ARGUS web application.
   - Review the headline latency statistics (mean 158.9s, median 130.4s), stage distributions, error ring buffer, and service statuses.

---

## Related Documents

- [System Architecture](./ARCHITECTURE.md)
- [Security & Governance](./SECURITY.md)
- [REST API Reference](./API.md)
- [Testing & Benchmark](./TESTING.md)
