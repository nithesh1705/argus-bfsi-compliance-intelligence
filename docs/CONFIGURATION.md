# ARGUS — Configuration & Environment Reference

Comprehensive specification of all runtime configuration parameters, feature flags, and environment variables across mock and live environments.

[Back to documentation index](./INDEX.md) | [Next: Development Guide](./DEVELOPMENT.md)

---

## Table of Contents

- [Overview & Configuration Hierarchy](#overview--configuration-hierarchy)
- [Complete Environment Variables Table](#complete-environment-variables-table)
- [Configuration Profiles](#configuration-profiles)
  - [Profile 1: Local Offline Mock Mode](#profile-1-local-offline-mock-mode)
  - [Profile 2: Google Cloud Live Production Mode](#profile-2-google-cloud-live-production-mode)
- [Related Documents](#related-documents)

---

## Overview & Configuration Hierarchy

ARGUS manages runtime settings through a type-safe Pydantic configuration class defined in [`../backend/core/config.py`](../backend/core/config.py). Variables prefixed with `ARGUS_` override internal defaults and can be set in:

1. System environment variables
2. Root `.env` file ([`../.env.example`](../.env.example))
3. Subdirectory `backend/.env` file

The system uses an explicit `PROVIDER_MODE` switch (`mock` vs `live`) to dictate whether adapters invoke offline deterministic components or live Google Cloud APIs (Vertex AI, Cloud Storage, Sensitive Data Protection, Cloud Trace).

---

## Complete Environment Variables Table

| Variable Name | Required (Mock) | Required (Live) | Default Value | Description | Example Placeholder |
|---|:---:|:---:|---|---|---|
| `ARGUS_PROVIDER_MODE` | No | Yes | `mock` | Execution mode adapter switch: `mock` (offline) or `live` (Vertex AI / GCP). | `mock` or `live` |
| `ARGUS_ENVIRONMENT` | No | No | `development` | Deployment environment label: `development`, `staging`, `production`. | `development` |
| `ARGUS_PROJECT_ID` | No | Yes | `your-gcp-project-id` | Google Cloud project identifier. | `<YOUR_GCP_PROJECT_ID>` |
| `ARGUS_PROJECT_NAME` | No | No | `argus-compliance-prod` | Human-readable Google Cloud project name. | `argus-compliance-prod` |
| `ARGUS_PROJECT_NUMBER` | No | Yes | `000000000000` | Google Cloud numeric project number. | `<YOUR_PROJECT_NUMBER>` |
| `ARGUS_REGION` | No | Yes | `asia-south1` | Regional resource location for Cloud SQL and Cloud Storage (Mumbai). | `<YOUR_REGION>` |
| `ARGUS_VERTEX_LOCATION` | No | Yes | `us-central1` | Endpoint region for Vertex AI model invocations. | `us-central1` |
| `ARGUS_GEMINI_FLASH_MODEL` | No | Yes | `gemini-3.5-flash` | Model identifier for detection, investigation, chat, and reasoning. | `gemini-3.5-flash` |
| `ARGUS_GEMINI_TRANSCRIBE_MODEL` | No | Yes | `gemini-3.5-flash` | Model identifier for audio transcription and acoustic diarization. | `gemini-3.5-transcribe` |
| `ARGUS_GEMINI_ROLE_MAPPING_MODEL` | No | Yes | `gemini-2.5-flash` | Model identifier for speaker label mapping and translation. | `gemini-2.5-flash` |
| `ARGUS_CALLS_BUCKET` | No | Yes | `argus-calls-incoming` | Cloud Storage bucket for incoming audio and permanent call archive. | `<YOUR_CALLS_BUCKET>` |
| `ARGUS_REGULATIONS_BUCKET` | No | Yes | `argus-regulations` | Cloud Storage bucket for statutory circular PDFs and documents. | `<YOUR_REGULATIONS_BUCKET>` |
| `ARGUS_DB_USER` | No | Yes | `root` | Database username for Cloud SQL MySQL connection. | `argus_user` |
| `ARGUS_DB_PASSWORD` | No | Yes | `qwerty12345` | Database user password. | `<YOUR_DB_PASSWORD>` |
| `ARGUS_DB_NAME` | No | Yes | `argus` | Relational database schema name. | `argus` |
| `ARGUS_DB_HOST` | No | No | `127.0.0.1` | Database host (local proxy, container IP, or Cloud SQL socket). | `127.0.0.1` |
| `ARGUS_DB_PORT` | No | No | `3306` | Database connection port. | `3306` |
| `ARGUS_INSTANCE_CONNECTION_NAME` | No | Yes (Cloud Run) | `None` | Cloud SQL instance connection string (`project:region:instance`). | `<YOUR_CLOUD_SQL_CONNECTION_NAME>` |
| `ARGUS_DB_IS_MOCK` | No | Yes | `true` (mock) / `false` (live) | Safety guard flag preventing synthetic test writes to live production DB. | `true` or `false` |
| `ARGUS_FS_STRATEGY` | No | No | `chunks` | File Search strategy: `chunks` (Strategy A) or `pdf` (Strategy B). | `chunks` |
| `ARGUS_FS_AUTH_MODE` | No | No | `vertex` | File Search authentication mode: `vertex` (ADC) or `api_key`. | `vertex` |
| `ARGUS_GEMINI_API_KEY` | No | No | `None` | Optional Gemini API key if using API key auth mode. | `<YOUR_GEMINI_API_KEY>` |
| `ARGUS_FILE_SEARCH_STORE_NAME` | No | No | `argus-regulation-store` | Logical identifier for the regulatory File Search store. | `argus-regulation-store` |
| `ARGUS_DLP_ENABLED` | No | No | `true` | Feature flag: Enable Sensitive Data Protection (DLP) PII redaction. | `true` |
| `ARGUS_MODEL_ARMOR_ENABLED` | No | No | `false` | Feature flag: Model Armor prompt screening (Tier 3 roadmap). | `false` |
| `ARGUS_FIREBASE_AUTH_ENABLED` | No | No | `false` | Feature flag: Firebase Authentication for end users (Tier 3 roadmap). | `false` |
| `ARGUS_CLOUD_TASKS_ENABLED` | No | No | `false` | Feature flag: Cloud Tasks queue dispatch (Tier 3 roadmap). | `false` |
| `ARGUS_OIDC_AUDIENCE` | No | Yes | `https://argus-backend-cloudrun-url` | Target audience URL expected in Eventarc Pub/Sub push OIDC tokens. | `https://<YOUR_BACKEND_URL>` |
| `ARGUS_ALLOWED_SERVICE_ACCOUNTS` | No | Yes | See config | Comma-separated list of service accounts allowed to push finalize events. | `["argus-eventarc-invoker-sa@<YOUR_GCP_PROJECT_ID>.iam.gserviceaccount.com"]` |
| `ARGUS_TRACE_ENABLED` | No | No | `true` | Feature flag: Enable OpenTelemetry distributed tracing to Cloud Trace. | `true` |
| `ARGUS_CLOUD_TRACE_DEEP_LINK_TEMPLATE` | No | No | See config | Deep link template to Google Cloud Trace Explorer. | `https://console.cloud.google.com/traces/explorer?project={project_id}&tid={trace_id}` |
| `ARGUS_JWT_SECRET` | No | Yes | Built-in fallback | Cryptographic secret key for signing session JWT tokens. | `<YOUR_SUPER_SECRET_JWT_KEY>` |
| `ARGUS_JWT_EXPIRATION_HOURS` | No | No | `24` | Token lifespan before expiration in hours. | `24` |
| `ARGUS_CORS_ORIGINS` | No | No | See config | Comma-separated list of allowed web origins for CORS headers. | `http://localhost:3000,http://localhost:5173` |
| `VITE_API_BASE_URL` | No | Yes | `http://localhost:8000` | Frontend configuration pointing to the backend API URL. | `https://<YOUR_BACKEND_URL>` |

---

## Configuration Profiles

### Profile 1: Local Offline Mock Mode
In offline mock mode, no Google Cloud credentials or cloud services are required. The system runs 100% locally using synthetic fixtures:

```ini
# .env (Local Mock Mode)
ARGUS_PROVIDER_MODE=mock
ARGUS_ENVIRONMENT=development
ARGUS_DB_HOST=127.0.0.1
ARGUS_DB_PORT=3306
ARGUS_DB_USER=root
ARGUS_DB_PASSWORD=qwerty12345
ARGUS_DB_NAME=argus
ARGUS_DB_IS_MOCK=true
ARGUS_DLP_ENABLED=true
ARGUS_TRACE_ENABLED=false
VITE_API_BASE_URL=http://localhost:8000
```

### Profile 2: Google Cloud Live Production Mode
In production mode on Cloud Run, the backend authenticates via Application Default Credentials (ADC) and connects to Cloud SQL via unix domain sockets:

```ini
# Production Environment Variables (Cloud Run)
ARGUS_PROVIDER_MODE=live
ARGUS_ENVIRONMENT=production
ARGUS_PROJECT_ID=<YOUR_GCP_PROJECT_ID>
ARGUS_PROJECT_NUMBER=<YOUR_PROJECT_NUMBER>
ARGUS_REGION=<YOUR_REGION>
ARGUS_VERTEX_LOCATION=us-central1
ARGUS_GEMINI_FLASH_MODEL=gemini-3.5-flash
ARGUS_GEMINI_TRANSCRIBE_MODEL=gemini-3.5-transcribe
ARGUS_GEMINI_ROLE_MAPPING_MODEL=gemini-2.5-flash
ARGUS_CALLS_BUCKET=<YOUR_CALLS_BUCKET>
ARGUS_REGULATIONS_BUCKET=<YOUR_REGULATIONS_BUCKET>
ARGUS_DB_USER=argus_user
ARGUS_DB_PASSWORD=<YOUR_DB_PASSWORD>
ARGUS_DB_NAME=argus
ARGUS_INSTANCE_CONNECTION_NAME=<YOUR_CLOUD_SQL_CONNECTION_NAME>
ARGUS_DB_IS_MOCK=false
ARGUS_OIDC_AUDIENCE=https://<YOUR_BACKEND_URL>
ARGUS_ALLOWED_SERVICE_ACCOUNTS=["argus-eventarc-invoker-sa@<YOUR_GCP_PROJECT_ID>.iam.gserviceaccount.com"]
ARGUS_TRACE_ENABLED=true
VITE_API_BASE_URL=https://<YOUR_BACKEND_URL>
```

---

## Related Documents

- [Development Guide](./DEVELOPMENT.md)
- [Deployment Guide](./DEPLOYMENT.md)
- [Security & Governance](./SECURITY.md)
- [REST API Reference](./API.md)
