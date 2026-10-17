# ARGUS — REST API Reference

Comprehensive specification of all REST API endpoints, schemas, authentication contracts, parameters, and error responses.

[Back to documentation index](./INDEX.md) | [Next: Frontend Architecture](./FRONTEND.md)

---

## Table of Contents

- [Overview & OpenAPI Specification](#overview--openapi-specification)
- [Authentication & Error Format](#authentication--error-format)
  - [JWT Bearer Authentication](#jwt-bearer-authentication)
  - [Standard Error Format](#standard-error-format)
  - [Case State Machine Conflicts (HTTP 409)](#case-state-machine-conflicts-http-409)
- [1. Health & Discovery Endpoints](#1-health--discovery-endpoints)
- [2. Events & Ingestion Triggers](#2-events--ingestion-triggers)
- [3. Dashboard Endpoints](#3-dashboard-endpoints)
- [4. Calls & Audio Streaming](#4-calls--audio-streaming)
- [5. Compliance Cases & Evidence Chain](#5-compliance-cases--evidence-chain)
- [6. Regulatory Corpus & Documents](#6-regulatory-corpus--documents)
- [7. Conversational AI Investigation Chat](#7-conversational-ai-investigation-chat)
- [8. System Diagnostics & Health](#8-system-diagnostics--health)
- [9. Authentication Routes](#9-authentication-routes)
- [10. Relationship Manager Analytics & Reports](#10-relationship-manager-analytics--reports)
- [11. Benchmark Evaluation](#11-benchmark-evaluation)
- [12. Observability & APM Telemetry](#12-observability--apm-telemetry)
- [13. Admin Portal & Master Data CRUD](#13-admin-portal--master-data-crud)
- [Related Documents](#related-documents)

---

## Overview & OpenAPI Specification

ARGUS exposes a modular REST API built with FastAPI. All endpoints (except Eventarc webhooks and health probes) are mounted under the `/api` route prefix.

- **Local Swagger UI:** Available at `http://localhost:8000/docs` when running locally.
- **OpenAPI 3.0 JSON Schema:** Available at `http://localhost:8000/openapi.json`.
- **Root Router:** [`../backend/main.py`](../backend/main.py)
- **Route Definitions:** [`../backend/api/routes/`](../backend/api/routes/)

---

## Authentication & Error Format

### JWT Bearer Authentication
Institutional endpoints require an `Authorization` header containing a valid signed JWT:
```http
Authorization: Bearer <JWT_TOKEN>
```
Tokens are generated via `POST /api/auth/login` and expire after 24 hours (configurable via `ARGUS_JWT_EXPIRATION_HOURS`).

### Standard Error Format
FastAPI validation errors and Starlette HTTP exceptions return structured JSON:

```json
{
  "error": "VALIDATION_ERROR",
  "message": "Invalid request parameters or payload.",
  "details": [
    {
      "loc": ["query", "limit"],
      "msg": "Input should be less than or equal to 200",
      "type": "less_than_equal"
    }
  ]
}
```

### Case State Machine Conflicts (HTTP 409)
To prevent race conditions between compliance officers reviewing the same case concurrently, state machine operations throw structured `HTTP 409 Conflict` responses:

- **`CaseAlreadyResolvedError`:**
  ```json
  {
    "error": "CASE_ALREADY_RESOLVED",
    "message": "Case CASE-001 has already been marked as RESOLVED by reviewer REV001.",
    "case_id": "CASE-001"
  }
  ```
- **`CaseAlreadyEscalatedError`:**
  ```json
  {
    "error": "CASE_ALREADY_ESCALATED",
    "message": "Case CASE-001 has already been escalated to the Compliance Committee.",
    "case_id": "CASE-001"
  }
  ```

---

## 1. Health & Discovery Endpoints

### `GET /`
- **Purpose:** Root probe check and API discovery banner.
- **Auth:** None.
- **Response Example (HTTP 200):**
  ```json
  {
    "status": "online",
    "service": "ARGUS Compliance Intelligence Platform API",
    "version": "1.0.0",
    "health": "/health",
    "docs": "/docs"
  }
  ```

### `GET /health` & `GET /api/health`
- **Purpose:** Lightweight container readiness probe for Cloud Run.
- **Auth:** None.
- **Response Example (HTTP 200):**
  ```json
  {
    "status": "ok",
    "service": "argus-backend",
    "version": "1.0.0",
    "mock_mode": false
  }
  ```

---

## 2. Events & Ingestion Triggers

### `POST /events/gcs`
- **Purpose:** Ingress webhook receiving Pub/Sub push messages wrapping Eventarc GCS object finalize notifications.
- **Auth:** Google OIDC Bearer Token (validated against `ARGUS_ALLOWED_SERVICE_ACCOUNTS`).
- **Request Payload:** Pub/Sub push message format wrapping base64-encoded GCS notification JSON.
- **Behavior:** Validates OIDC token, decodes payload, extracts object name, and adds `run_pipeline_for_object` to a `BackgroundTask`. Returns HTTP 200 immediately to avoid Pub/Sub retry storms.
- **Response Example (HTTP 200):**
  ```json
  {
    "status": "ACK_SCHEDULED",
    "object_name": "RM001_CUST001_20260310_1030.wav"
  }
  ```

### `POST /api/pipeline/process-now`
- **Purpose:** Reviewer-triggered on-demand pipeline execution for an existing audio object in Cloud Storage.
- **Auth:** Bearer JWT.
- **Request Body:**
  ```json
  {
    "object_name": "RM001_CUST001_20260310_1030.wav"
  }
  ```
- **Response Example (HTTP 200):**
  ```json
  {
    "status": "SCHEDULED",
    "object_name": "RM001_CUST001_20260310_1030.wav"
  }
  ```

---

## 3. Dashboard Endpoints

### `GET /api/dashboard/summary`
- **Purpose:** Returns high-density surveillance KPIs, trend charts, category breakdown, recent critical cases, and real latency statistics for the Operational Dashboard.
- **Auth:** Bearer JWT.
- **Response Example (HTTP 200):**
  ```json
  {
    "kpis": {
      "total_calls_monitored": 12,
      "violations_detected": 8,
      "open_cases_count": 5,
      "resolved_cases_count": 3,
      "high_severity_count": 3,
      "average_latency_seconds": 158.9
    },
    "severity_distribution": {
      "HIGH": 3,
      "MEDIUM": 3,
      "LOW": 2
    },
    "category_breakdown": [
      {"category": "GUARANTEED_RETURN", "count": 4},
      {"category": "SUITABILITY_MISMATCH", "count": 3},
      {"category": "MISSING_RISK_DISCLOSURE", "count": 1}
    ],
    "recent_cases": [...]
  }
  ```

---

## 4. Calls & Audio Streaming

### `GET /api/calls`
- **Purpose:** Paginated, filterable roster of all monitored sales calls.
- **Auth:** Bearer JWT.
- **Query Parameters:**
  - `rm_id` (string, optional)
  - `customer_id` (string, optional)
  - `severity` (string, optional: `HIGH`, `MEDIUM`, `LOW`)
  - `status` (string, optional: `RECEIVED`, `COMPLETED`, `FAILED`)
  - `has_violation` (boolean, optional)
  - `limit` (int, default 50, max 200)
  - `offset` (int, default 0)
- **Response Example (HTTP 200):**
  ```json
  {
    "total": 12,
    "limit": 50,
    "offset": 0,
    "items": [
      {
        "id": "CALL_RM001_CUST001_20260310_1030",
        "rm_id": "RM001",
        "rm_name": "Rajesh Kumar",
        "customer_id": "CUST001",
        "customer_name": "Sunita Sharma",
        "duration_s": 245.5,
        "status": "COMPLETED",
        "has_violation": true,
        "finding_count": 2,
        "severity": "HIGH",
        "date_time": "2026-03-10 10:30:00"
      }
    ]
  }
  ```

### `GET /api/calls/{call_id}`
- **Purpose:** Full call detail including all diarized, timestamped, PII-redacted transcript segments.
- **Auth:** Bearer JWT.
- **Response Example (HTTP 200):**
  ```json
  {
    "id": "CALL_RM001_CUST001_20260310_1030",
    "rm_id": "RM001",
    "customer_id": "CUST001",
    "duration_s": 245.5,
    "status": "COMPLETED",
    "transcript_segments": [
      {
        "segment_id": 1,
        "idx": 0,
        "speaker_label": "Speaker 1",
        "role": "RM",
        "start_ms": 1000,
        "end_ms": 4200,
        "text_original": "Good morning Sunita ji, Rajesh here from Wealth Advisory.",
        "text_english": "Good morning Sunita ji, Rajesh here from Wealth Advisory.",
        "is_violation": false
      }
    ]
  }
  ```

### `GET /api/calls/{call_id}/audio`
- **Purpose:** Streams the call audio file through the backend from Cloud Storage.
- **Auth:** Bearer JWT (or query token).
- **HTTP Range Support (RFC 7233):** Supports `Range: bytes=start-end` headers, returning `HTTP 206 Partial Content`. This is required for WaveSurfer.js waveform rendering and seeking.
- **Headers Returned:**
  - `Content-Type`: `audio/wav` or `audio/mpeg`
  - `Accept-Ranges`: `bytes`
  - `Content-Range`: `bytes start-end/total`

---

## 5. Compliance Cases & Evidence Chain

### `GET /api/cases`
- **Purpose:** Paginated list of compliance cases with dynamically computed `needs_review` flag.
- **Auth:** Bearer JWT.
- **Query Parameters:** `status`, `severity`, `rm_id`, `call_id`, `needs_review`, `limit`, `offset`.
- **Response Structure:** Array of case items with metadata and finding summaries.

### `GET /api/cases/{case_id}`
- **Purpose:** Assembles and returns the complete, auditable Evidence Chain for a case.
- **Auth:** Bearer JWT.
- **Response Example (HTTP 200):**
  ```json
  {
    "case_id": "CASE-RM001_CUST001_20260310_1030_1",
    "finding_id": "FND-RM001_CUST001_20260310_1030_1",
    "call_id": "CALL_RM001_CUST001_20260310_1030",
    "rm_id": "RM001",
    "rm_name": "Rajesh Kumar",
    "customer_id": "CUST001",
    "customer_name": "Sunita Sharma",
    "customer_risk_profile": "Conservative",
    "customer_experience": "Low",
    "category": "GUARANTEED_RETURN",
    "severity": "HIGH",
    "status": "OPEN",
    "escalated": false,
    "confidence": 0.98,
    "timestamp_start": 14,
    "timestamp_end": 22,
    "quote_original": "Sir, this fund gives an 18% guaranteed return every year without any risk.",
    "quote_english": "Sir, this fund gives an 18% guaranteed return every year without any risk.",
    "regulation": {
      "chunk_id": "SEBI_DIST_COND_2022_P03_C01",
      "citation_label": "SEBI Code of Conduct for Mutual Fund Distributors Clause 2(a)",
      "source_url": "https://www.sebi.gov.in/legal/circulars/apr-2022/code-of-conduct-for-mutual-fund-distributors",
      "page_number": 3
    },
    "evidence": {
      "supporting": ["Explicit guarantee of 18% return", "High-risk equity scheme"],
      "contradicting": [],
      "rationale": "Distributors are prohibited from assuring returns on market-linked securities."
    },
    "activity_log": [
      {
        "action": "CREATED",
        "actor": "SYSTEM",
        "details": "Case generated by ARGUS Investigation Agent",
        "timestamp": "2026-10-15T06:53:49"
      }
    ]
  }
  ```

### `PATCH /api/cases/{case_id}/status`
- **Purpose:** Atomically resolves a case as reviewed or dismissed.
- **Auth:** Bearer JWT.
- **Request Body:**
  ```json
  {
    "reviewer_id": "USR-001",
    "action": "mark_reviewed",
    "notes": "Reviewed with RM. Warning issued."
  }
  ```
- **HTTP Status Codes:** `200 OK`, `404 Not Found`, `409 Conflict` (if case already resolved).

### `POST /api/cases/{case_id}/escalate`
- **Purpose:** Escalates a case to the Compliance Committee.
- **Auth:** Bearer JWT.
- **Request Body:**
  ```json
  {
    "reviewer_id": "USR-001",
    "notes": "Requires committee review due to repeated guarantee violations."
  }
  ```
- **HTTP Status Codes:** `200 OK`, `404 Not Found`, `409 Conflict` (if already escalated).

### `POST /api/cases/{case_id}/assign`
- **Purpose:** Assigns or reassigns case ownership to a compliance officer.
- **Auth:** Bearer JWT.
- **Request Body:** `{"reviewer_id": "USR-001", "assigned_to": "USR-002"}`

### `POST /api/cases/{case_id}/notes`
- **Purpose:** Appends an immutable note to the case activity audit log.
- **Auth:** Bearer JWT.
- **Request Body:** `{"reviewer_id": "USR-001", "notes": "Audited with branch head."}`

---

## 6. Regulatory Corpus & Documents

> [!NOTE]
> Endpoints are mounted identically on both `/api/documents` and `/api/regulations` for frontend compatibility.

### `GET /api/regulations` & `GET /api/documents`
- **Purpose:** Lists statutory master documents with chunk counts and storage paths.
- **Auth:** Bearer JWT.

### `GET /api/regulations/{doc_id}/preview` & `GET /api/documents/{doc_id}/preview`
- **Purpose:** Streams the document inline (`application/pdf` or `text/plain`) for browser preview.
- **Auth:** Bearer JWT.

### `GET /api/regulations/{doc_id}/download` & `GET /api/documents/{doc_id}/download`
- **Purpose:** Downloads the document attachment.
- **Auth:** Bearer JWT.

### `POST /api/regulations/upload` & `POST /api/documents/upload`
- **Purpose:** Multipart file upload of a new regulatory document. Automatically uploads file to Cloud Storage, extracts text, chunks clauses, and registers chunks in Cloud SQL.
- **Auth:** Bearer JWT.
- **Form Data:** `file` (binary), `document_name` (string), `regulator` (string), `year` (int).

### `DELETE /api/regulations/{doc_id}` & `DELETE /api/documents/{doc_id}`
- **Purpose:** Permanently deletes a statutory document and prunes its associated chunks from `regulation_chunk_registry`.
- **Auth:** Bearer JWT.

---

## 7. Conversational AI Investigation Chat

### `POST /api/chat/message`
- **Purpose:** Submits an investigative query to the read-only AI chat assistant.
- **Auth:** Bearer JWT.
- **Request Body:**
  ```json
  {
    "message": "Which RMs have repeated guaranteed return violations?",
    "session_id": "session-101",
    "history": []
  }
  ```
- **Response Example (HTTP 200):**
  ```json
  {
    "reply": "Based on surveillance records, RM001 (Rajesh Kumar) has 2 confirmed GUARANTEED_RETURN findings...",
    "response_text": "Based on surveillance records, RM001 (Rajesh Kumar) has 2 confirmed GUARANTEED_RETURN findings...",
    "tools_called": [
      {"name": "search_findings_summary", "arguments": {"category": "GUARANTEED_RETURN"}}
    ],
    "grounded_results": [
      {
        "finding_id": "FND-001",
        "category": "GUARANTEED_RETURN",
        "severity": "HIGH",
        "citation_label": "SEBI Code of Conduct Clause 2(a)"
      }
    ],
    "provider_used": "Google Cloud Gemini Flash"
  }
  ```

---

## 8. System Diagnostics & Health

### `GET /api/system/health`
- **Purpose:** Hybrid health check providing live database and storage connectivity checks alongside cached last-known provider statuses (zero LLM ping cost).
- **Auth:** None (or Bearer JWT).
- **Response Structure:** Live status for MySQL and Cloud Storage, active model IDs, trace deep link template.

### `GET /api/system/diagnostics`
- **Purpose:** Statistical latency breakdown (mean, median, min, max durations in ms) across all pipeline stages.
- **Auth:** Bearer JWT.

---

## 9. Authentication Routes

### `POST /api/auth/login`
- **Purpose:** Validates username/email and password, returns signed Bearer JWT and user profile.
- **Auth:** None.
- **Request Body:** `{"username": "admin", "password": "admin12345"}`
- **Response Example (HTTP 200):**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "user": {
      "user_id": "USR-001",
      "username": "admin",
      "email": "audit.officer@argus.com",
      "role": "Audit Officer",
      "team": "Compliance",
      "access": "All",
      "full_name": "Audit Officer"
    }
  }
  ```

### `GET /api/auth/me`
- **Purpose:** Validates existing session token and returns active profile.
- **Auth:** Bearer JWT.

### `POST /api/auth/logout`
- **Purpose:** Terminates current user session.
- **Auth:** Bearer JWT.

---

## 10. Relationship Manager Analytics & Reports

### `GET /api/rm`
- **Purpose:** Returns RM roster with surveillance stats, violation rates, and computed risk scores.
- **Auth:** Bearer JWT.

### `GET /api/rm/{rm_id}/analytics`
- **Purpose:** Complete dossier analytics, category breakdown, and case history for an RM.
- **Auth:** Bearer JWT.

### `POST /api/rm/{rm_id}/report/email`
- **Purpose:** Compiles and dispatches an authoritative HTML compliance report email for an RM.
- **Auth:** Bearer JWT.
- **Request Body:**
  ```json
  {
    "recipients": ["compliance.head@institution.com"],
    "request_id": "req-uuid-101"
  }
  ```
- **Idempotency:** Cached `request_id` values return an idempotent replay without re-dispatching emails.

---

## 11. Benchmark Evaluation

### `GET /api/benchmark`
- **Purpose:** Returns the latest comparative 3-way evaluation report comparing the Keyword Baseline, Gemini Detection Only, and Full ARGUS Pipeline.
- **Auth:** Bearer JWT.
- **Source:** [`../backend/benchmark/run_benchmark.py`](../backend/benchmark/run_benchmark.py)

---

## 12. Observability & APM Telemetry

### `GET /api/observability/summary`
- **Purpose:** High-level APM KPIs (total calls processed, failure rate, average latency).

### `GET /api/observability/pipeline`
- **Purpose:** Statistical stage distributions (`ingestion`, `detection`, `investigation`, `end_to_end`).

### `GET /api/observability/errors`
- **Purpose:** Real-time error ring buffer capturing pipeline failures.

### `GET /api/observability/services`
- **Purpose:** Live connectivity probe for MySQL, Vector Registry, and Gemini.

---

## 13. Admin Portal & Master Data CRUD

Mounted under `/api/admin/*`:

- `GET /api/admin/analytics` — Executive time-series analytics and chart aggregations.
- `GET`, `POST`, `PUT /api/admin/users/{user_id}`, `DELETE` — System users CRUD.
- `GET`, `POST`, `PUT /api/admin/rms/{rm_id}`, `DELETE` — Relationship Managers roster CRUD.
- `GET`, `POST`, `PUT /api/admin/customers/{customer_id}`, `DELETE` — Customer investment profiles CRUD.
- `GET`, `POST`, `PUT /api/admin/products/{product_id}`, `DELETE` — Product scheme catalog CRUD.
- `GET`, `POST`, `PUT /api/admin/authorities/{authority_id}`, `DELETE` — Regulatory authorities CRUD.

---

## Related Documents

- [System Architecture](./ARCHITECTURE.md)
- [Data Model & Schema](./DATA_MODEL.md)
- [Frontend Architecture](./FRONTEND.md)
- [Security & Governance](./SECURITY.md)
