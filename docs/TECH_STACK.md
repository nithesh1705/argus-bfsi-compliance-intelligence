# ARGUS — Technology Stack & Dependencies

Comprehensive technical breakdown of frameworks, cloud services, libraries, versions, and selection rationale across ARGUS.

[Back to documentation index](./INDEX.md) | [Next: Agents & Hard Guardrails](./AGENTS.md)

---

## Table of Contents

- [Google Cloud Platform Services](#google-cloud-platform-services)
- [Artificial Intelligence & Language Models](#artificial-intelligence--language-models)
- [Backend Framework & Libraries](#backend-framework--libraries)
- [Frontend Architecture & Libraries](#frontend-architecture--libraries)
- [Observability & Distributed Tracing](#observability--distributed-tracing)
- [Security, Authentication & Data Protection](#security-authentication--data-protection)
- [Containerization, Build & Deployment](#containerization-build--deployment)
- [Infrastructure Cost Profile (Estimates)](#infrastructure-cost-profile-estimates)
- [Related Documents](#related-documents)

---

## Google Cloud Platform Services

| Service | Category | Role in ARGUS | Selection Rationale |
|---|---|---|---|
| **Google Cloud Run** | Serverless Compute | Hosts `argus-backend` (FastAPI) and `argus-frontend` (Nginx/Vite). | Serverless scale-to-zero, per-request billing, instant container deployments, and native Cloud SQL connector support. |
| **Google Cloud Storage (GCS)** | Object Storage | Stores incoming call recordings (`calls/incoming/`), archived calls (`calls/archive/`), and regulatory PDFs (`regulations/`). | Highly durable, uniform bucket access, sub-second latency, and native Eventarc integration. |
| **Google Eventarc** | Event Broker | Captures GCS `object.v1.finalized` events and triggers Pub/Sub push. | Decoupled event routing with automatic retries and native Cloud Run target integration. |
| **Google Cloud Pub/Sub** | Asynchronous Messaging | Buffers GCS object finalization notifications and pushes them via authenticated OIDC. | Guaranteed delivery, poison-pill isolation, and peak load absorption. |
| **Cloud SQL for MySQL 8.0** | Relational Database | Authoritative storage for 19 tables including calls, candidates, investigations, findings, cases, and regulation chunks. | Full ACID compliance, foreign key constraints, robust indexing, and transaction guarantees. |
| **Sensitive Data Protection (DLP)** | Data Privacy | Scans and de-identifies statutory Indian identity types (PAN, Aadhaar, cards, phone, email) in audio transcripts. | Enterprise-grade regulatory PII masking with built-in Indian info types. |
| **Google Cloud Trace** | Distributed Tracing | End-to-end distributed span collection across all pipeline stages. | Native OpenTelemetry integration, minimal overhead, and deep linking from compliance case records. |
| **Google Cloud Logging** | Centralized Logging | Captures structured JSON logs with trace correlation across Cloud Run instances. | Integrated query capabilities and error indexing. |
| **Secret Manager** | Secret Storage | Manages database credentials, JWT secrets, and API keys. | Immutable versioned secret management with IAM-based access control. |
| **Artifact Registry** | Container Registry | Stores Docker images for backend and frontend services. | Secure, region-local container image repository. |

---

## Artificial Intelligence & Language Models

| Model / Service | Role in ARGUS | Configuration Parameter | Selection Rationale |
|---|---|---|---|
| **Gemini Flash (`gemini-3.5-flash`)** | Core reasoning model for candidate detection, statutory investigation, guardrail validation, and multi-turn AI chat. | `ARGUS_GEMINI_FLASH_MODEL` (default: `gemini-3.5-flash`) | State-of-the-art reasoning latency, large context window, native structured JSON output schema support, and tool calling. |
| **Gemini Flash (`gemini-2.5-flash`)** | Speaker role mapping and multilingual translation (Hindi, Tamil, Hinglish to English). | `ARGUS_GEMINI_ROLE_MAPPING_MODEL` (default: `gemini-2.5-flash`) | High-speed, cost-effective structured speaker label resolution and dialect comprehension. |
| **Gemini Audio / Transcribe** | Multilingual audio transcription and acoustic speaker diarization. | `ARGUS_GEMINI_TRANSCRIBE_MODEL` (default: `gemini-3.5-flash` / `gemini-3.5-transcribe`) | Native audio understanding with custom vocabulary injection from the product catalog. |
| **Gemini File Search Store** | Regulatory clause retrieval and vector grounding. | `ARGUS_FILE_SEARCH_STORE_NAME` (default: `argus-regulation-store`) | Built-in semantic search over regulatory circulars and statutory amendments without requiring an external vector database. |

Source implementation: [`../backend/core/config.py`](../backend/core/config.py)

---

## Backend Framework & Libraries

From [`../backend/requirements.txt`](../backend/requirements.txt):

| Package | Version Range | Role in ARGUS | Selection Rationale |
|---|---|---|---|
| **FastAPI** | `>=0.115.0, <1.0.0` | Core asynchronous web framework and REST API engine. | Native async support, automatic OpenAPI schema generation, dependency injection, and Pydantic v2 integration. |
| **Uvicorn** | `>=0.30.0, <1.0.0` | High-performance ASGI web server. | Low overhead, reliable event loop, and production stability. |
| **Pydantic** | `>=2.7.0, <3.0.0` | Data validation, domain DTOs, and structured LLM output schemas. | Extreme validation speed (Rust core), strict typing, and structured JSON output guarantees. |
| **pydantic-settings** | `>=2.0.0, <3.0.0` | Environment configuration management with `.env` file loading. | Centralized type-safe settings with prefix support. |
| **SQLAlchemy** | `>=2.0.0, <3.0.0` | Connection pool management and SQL expression utilities. | Robust database connection pooling and thread safety. |
| **PyMySQL** | `>=1.1.0, <2.0.0` | Pure-Python MySQL client driver. | Native Cloud SQL Connector compatibility and cross-platform reliability. |
| **PyJWT** | `>=2.8.0` | RFC 7519 JSON Web Token issuance and decoding. | Industry standard token authentication for institutional audit sessions. |
| **bcrypt** | `>=4.0.0` | Password hashing with cryptographic salts (rounds=12). | Resistant to rainbow-table and brute-force attacks. |
| **pypdf** | `>=3.0.0` | Regulatory PDF text extraction and statutory clause chunking. | In-process PDF extraction without heavy binary external dependencies. |
| **google-genai** | `>=0.1.0` | Official Google GenAI SDK for Gemini model invocation. | First-party integration with Gemini 2.5 and 3.5 model families. |
| **google-cloud-storage** | `>=2.18.0` | Cloud Storage API client for audio and document objects. | Chunked streaming, upload/download resilience, and metadata operations. |
| **google-cloud-dlp** | `>=3.18.0` | Sensitive Data Protection API client for PII redaction. | High-throughput in-line inspection and token masking. |

---

## Frontend Architecture & Libraries

From [`../frontend/package.json`](../frontend/package.json):

| Package | Version | Role in ARGUS | Selection Rationale |
|---|---|---|---|
| **React** | `^18.3.1` | Declarative UI framework with Concurrent Mode support. | Component-driven architecture and ecosystem maturity. |
| **Vite** | `^6.2.0` | Modern frontend build tool and development server. | Sub-second Hot Module Replacement (HMR) and optimized rollup production bundles. |
| **TypeScript** | `^5.7.3` | Static typing across components, hooks, and services. | Strict contract enforcement between API DTOs and UI state. |
| **Tailwind CSS** | `^3.4.17` | Utility-first CSS framework with custom design tokens. | Zero-runtime CSS, consistent spacing, and dark/light mode token integration. |
| **WaveSurfer.js** | `^7.9.1` | Interactive audio waveform visualizer with timeline seeking. | Canvas-rendered audio playback, zoom controls, and click-to-timestamp seeking. |
| **React Router** | `^6.30.0` | Client-side routing and protected route management. | URL-driven state, deep-linking, and nested route layouts. |
| **Recharts** | `^2.15.1` | Dynamic data visualization (trend lines, severity bar charts). | Responsive SVG charting with theme-aware styling. |
| **Lucide React** | `^1.16.0` | Iconography across sidebar, tables, and action modals. | Modern, clean icon suite with consistent stroke weights. |
| **React Markdown & Remark GFM** | `^10.1.0` / `^4.0.1` | Renders structured evidence rationales and AI chat markdown. | GitHub-flavored markdown parsing with table and link support. |

---

## Observability & Distributed Tracing

From [`../backend/requirements.txt`](../backend/requirements.txt) and [`../backend/observability/`](../backend/observability/):

| Technology | Version Range | Role in ARGUS | Selection Rationale |
|---|---|---|---|
| **OpenTelemetry API & SDK** | `>=1.25.0` | Vendor-neutral distributed instrumentation framework. | Standardized span creation, context propagation, and attribute tagging. |
| **opentelemetry-exporter-gcp-trace** | `>=1.6.0` | Direct exporter pushing spans to Google Cloud Trace. | Native Cloud Trace Explorer correlation without intermediate collector daemons. |
| **Structured JSON Logging** | Standard Library | Outputs machine-readable logs tagged with `trace_id` and `call_id`. | Instant trace correlation in Google Cloud Logs Explorer. |

---

## Security, Authentication & Data Protection

| Component | Standard / Mechanism | Implementation File |
|---|---|---|
| **Identity De-identification** | Google Cloud Sensitive Data Protection (DLP) API | [`../backend/adapters/pii_redactor.py`](../backend/adapters/pii_redactor.py) |
| **Session Authentication** | JSON Web Tokens (HMAC-SHA256, 24-hour expiration) | [`../backend/workflows/user_service.py`](../backend/workflows/user_service.py) |
| **Password Storage** | bcrypt with 12 salt rounds | [`../backend/workflows/user_service.py`](../backend/workflows/user_service.py) |
| **Eventarc Ingress Auth** | Google Cloud OIDC Bearer Token Verification | [`../backend/api/routes/events.py`](../backend/api/routes/events.py) |
| **Least-Privilege IAM** | Service Accounts (`argus-backend-sa`, `argus-eventarc-invoker-sa`) | [`../infra/setup.sh`](../infra/setup.sh) |
| **Secret Management** | Google Cloud Secret Manager | [`../infra/setup.sh`](../infra/setup.sh) |

---

## Containerization, Build & Deployment

| Technology | Configuration File | Purpose |
|---|---|---|
| **Multi-Stage Docker (Backend)** | [`../backend/Dockerfile`](../backend/Dockerfile) | Python 3.11-slim runtime with dependency caching and non-root execution. |
| **Multi-Stage Docker (Frontend)** | [`../frontend/Dockerfile`](../frontend/Dockerfile) | Node build stage compiling Vite bundle, served via high-performance Nginx. |
| **Cloud Build Pipelines** | [`../CloudBuild/cloudbuild.yaml`](../CloudBuild/cloudbuild.yaml) | Automated container compilation and deployment to Cloud Run. |
| **Infrastructure Scripts** | [`../infra/setup.sh`](../infra/setup.sh), [`../infra/deploy.sh`](../infra/deploy.sh) | Automated GCP API enablement, Cloud SQL provisioning, and IAM binding. |

---

## Infrastructure Cost Profile (Estimates)

> [!NOTE]
> All figures below are **estimates** based on standard Google Cloud list pricing for region `asia-south1` (Mumbai) and Vertex AI pricing as of October 2026. Actual costs vary based on concurrency, storage duration, and sustained commitment discounts.

| Service / Resource | Sizing / Tier | Estimated Monthly Cost (Judging / Dev) | Estimated Per-Call Cost |
|---|---|:---:|:---:|
| **Cloud Run (Backend + Frontend)** | Scale to zero (min instances = 0, 2 CPU / 2GB RAM backend, 0.5 CPU / 512MB frontend) | ~$0.00 to $5.00 / month | < $0.001 per invocation |
| **Cloud SQL for MySQL** | `db-f1-micro` (1 vCPU, 0.6 GB RAM, 10 GB SSD, no HA) | ~$10.00 to $12.00 / month | Amortized baseline |
| **Cloud Storage** | Standard Storage (< 5 GB audio and regulations) | < $0.20 / month | Negligible |
| **Vertex AI: Gemini Flash** | Audio: ~$0.00002/sec (~$0.0012/min)<br>Text: $0.075 / 1M input tokens, $0.30 / 1M output tokens | Pay-per-use | **~$0.005 to $0.015 per 5-min call** |
| **Sensitive Data Protection (DLP)** | Content inspection & de-identification | Pay-per-use | **~$0.002 per call** |
| **Cloud Trace & Logging** | Free allotment (first 2.5M spans, 50 GB logs free) | $0.00 | $0.00 |
| **Total Estimated Operating Cost** | Continuous staging environment with active testing | **~$15.00 to $25.00 / month** | **~$0.01 to $0.02 per call** |

---

## Related Documents

- [System Architecture](./ARCHITECTURE.md)
- [Agents & Hard Guardrails](./AGENTS.md)
- [Data Model & Schema](./DATA_MODEL.md)
- [Deployment Guide](./DEPLOYMENT.md)
