# ARGUS — Local Development & Contribution Guide

Developer reference for local offline setup, mock mode execution, project folder structure, coding conventions, and troubleshooting.

[Back to documentation index](./INDEX.md) | [Next: Deployment Guide](./DEPLOYMENT.md)

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start: Local Offline Mock Mode](#quick-start-local-offline-mock-mode)
  - [1. Clone and Configure Environment](#1-clone-and-configure-environment)
  - [2. Backend Setup](#2-backend-setup)
  - [3. Local Database & Mock Storage Initialization](#3-local-database--mock-storage-initialization)
  - [4. Frontend Setup](#4-frontend-setup)
- [Repository Folder Map](#repository-folder-map)
- [Testing Guidelines](#testing-guidelines)
- [Coding Conventions](#coding-conventions)
- [Extending the Platform](#extending-the-platform)
  - [Adding a New API Endpoint](#adding-a-new-api-endpoint)
  - [Adding a New Surveillance Tool](#adding-a-new-surveillance-tool)
- [Troubleshooting & Common Pitfalls](#troubleshooting--common-pitfalls)
- [Related Documents](#related-documents)

---

## Prerequisites

Ensure the following runtimes and tools are installed:

- **Python:** Version 3.11+
- **Node.js:** Version 20+ (with `npm`)
- **Database:** Local MySQL 8.0 server (or Docker container running MySQL 8.0)
- **Git:** Standard git client

No Google Cloud credentials, cloud service accounts, or external API keys are required for offline mock development.

---

## Quick Start: Local Offline Mock Mode

### 1. Clone and Configure Environment

Copy the template configuration file to `.env`:

```bash
cp .env.example .env
```

Verify that `ARGUS_PROVIDER_MODE=mock` is set in `.env` to enforce offline execution.

### 2. Backend Setup

Create and activate a virtual environment, then install Python dependencies:

```bash
python -m venv .venv
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On Linux / macOS:
source .venv/bin/activate

pip install -r backend/requirements.txt
```

### 3. Local Database & Mock Storage Initialization

Start your local MySQL 8.0 server (listening on `127.0.0.1:3306`). Then run the idempotent database and storage setup scripts:

```bash
# Initialize local mock storage directories (data/storage/calls/incoming, regulations)
python scripts/init_mock_storage.py

# Create MySQL schema and seed master rosters (RMs, customers, products)
python scripts/init_argus_db.py

# Pre-index statutory circular chunks into Cloud SQL
python scripts/ingest_regulations.py
```

Start the FastAPI backend server:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

The backend API will be accessible at `http://localhost:8000`. Interactive OpenAPI documentation is available at `http://localhost:8000/docs`.

### 4. Frontend Setup

In a new terminal window, install frontend dependencies and launch the Vite dev server:

```bash
cd frontend
npm install
npm run dev
```

The user interface will be accessible at `http://localhost:5173`. Default local seed credentials for login:
- **Username:** `admin`
- **Password:** `admin12345`

---

## Repository Folder Map

```
argus/
├── backend/                       # Python FastAPI Backend
│   ├── adapters/                  # Dual-mode infrastructure adapters (Storage, LLM, DLP, DB)
│   ├── agents/                    # Multi-agent implementations (Detection, Investigation, Chat)
│   ├── api/routes/                # Modular REST API endpoints
│   ├── benchmark/                 # 3-way comparative benchmark suite & ground truth
│   ├── core/                      # Configuration, settings singleton, path constants
│   ├── db/                        # PyMySQL session management & repository queries
│   │   └── repositories/          # Domain repositories (cases, calls, rm, admin)
│   ├── indexing/                  # Regulation extraction, clause parsing, chunk schemas
│   ├── ingestion/                 # Telephony ingestion agent, filename parser, pipeline runner
│   ├── observability/             # Cloud Trace OpenTelemetry exporters & structured logging
│   ├── reports/                   # RM compliance dossier renderer & email dispatcher
│   ├── schemas/                   # Pydantic domain models & request/response DTOs
│   ├── tests/                     # Unit and integration test suites
│   ├── Dockerfile                 # Multi-stage production container build
│   ├── main.py                    # Application entrypoint & exception handlers
│   └── requirements.txt           # Python dependency specifications
│
├── frontend/                      # React 18 + TypeScript + Vite UI
│   ├── src/
│   │   ├── components/            # Layout, auth, reports, and shared widgets
│   │   │   ├── layout/            # Sidebar, Topbar, AppShell, OwlThemeToggle
│   │   │   └── shared/            # AudioPlayer, EvidenceChainPanel, TranscriptViewer
│   │   ├── context/               # AuthContext, ThemeContext, SidebarContext
│   │   ├── pages/                 # Route pages (Calls, Cases, Dashboard, Regulations, etc.)
│   │   ├── services/              # Axios/Fetch API client integrations
│   │   ├── styles/                # Tailwind CSS global styles & HSL theme tokens
│   │   ├── types/                 # Shared TypeScript interfaces & types
│   │   ├── App.tsx                # Context providers & toast container
│   │   ├── router.tsx             # Route table & role-based routing
│   │   └── main.tsx               # DOM root mounting
│   ├── Dockerfile                 # Production Nginx multi-stage build
│   └── package.json               # NPM scripts & package dependencies
│
├── data/                          # Seed data & schema scripts
│   ├── audio/                     # Synthetic test call recordings (.wav)
│   ├── schemas/                   # argus_mysql_ddl.sql and seed scripts
│   └── storage/                   # Local simulated object store in mock mode
│
├── docs/                          # Comprehensive technical documentation
│   └── glimpse/                   # Numbered UI screenshots in dark/ and light/
│
├── infra/                         # Cloud infrastructure automation scripts
│   ├── setup.sh                   # GCP API enablement, Cloud SQL, and IAM setup
│   ├── deploy.sh                  # Container build & Cloud Run deployment
│   └── teardown.sh                # Resource cleanup & cost control
│
├── RegulatoryDocs/                # Official statutory PDFs (SEBI, AMFI circulars)
├── scripts/                       # Operational, migration, and verification scripts
│   ├── check_docs_links.py        # Case-exact documentation link & anchor verifier
│   ├── init_argus_db.py           # Database migration & seed runner
│   └── init_mock_storage.py       # Mock filesystem storage initializer
│
├── tests/                         # End-to-end and Phase 2 test suites
│   ├── results/                   # Recorded test outputs and table dumps
│   └── test_files/                # Automated verification suites (T0 to T12)
│
├── .env.example                   # Environment configuration template
├── cloudbuild.yaml                # Automated Cloud Build deployment pipeline
└── docker-compose.yml             # Local MySQL container definition
```

---

## Testing Guidelines

ARGUS maintains two distinct test layers:

### 1. Offline Unit & Adapter Tests
These tests execute 100% offline using synthetic fixtures and deterministic mock adapters. Run them from the project root using `python -m pytest`:

```bash
# Execute offline unit tests
python -m pytest backend/tests/test_ingestion_phase1d.py
```

### 2. Documentation Link & Case Sensitivity Checker
To ensure documentation integrity, run the repository link verification script:

```bash
python scripts/check_docs_links.py
```
This utility validates that all relative file links exist with exact casing, anchors resolve to actual headings, and forbidden project literals remain masked.

---

## Coding Conventions

1. **Strict Type Annotations:** All Python functions must include parameter and return type hints (`typing.Optional`, `typing.List`, `typing.Dict`).
2. **Pydantic Validation:** All external request payloads and structured LLM responses must be defined as Pydantic models in [`../backend/schemas/`](../backend/schemas/) or adjacent agent modules.
3. **Dual Provider Pattern:** External service interactions (LLM, Storage, DLP, Retriever) must implement an Abstract Base Class (ABC) with separate `Mock` and `Live` subclasses. Direct invocation of external cloud APIs without an adapter is prohibited.
4. **Defensive Database Queries:**
   - Always escape the MySQL table name `` `call` `` with backticks to prevent syntax errors with the reserved keyword.
   - Use parameterized queries (`%s`) exclusively to prevent SQL injection.
   - Keep transactions concise: use `with db_manager.transaction() as cur:` for writes.
5. **Structured Logging:** Use module-specific loggers (`logger = logging.getLogger("argus.<module>")`) and output structured metadata. Never log raw customer identity data or unredacted PII.
6. **Frontend Design Tokens:** Never hardcode ad-hoc hex colors. Always reference CSS custom properties or Tailwind semantic tokens (`dark:bg-slate-900`, `text-slate-100`, `border-slate-200/80`).

---

## Extending the Platform

### Adding a New API Endpoint
1. Define request/response Pydantic models in [`../backend/schemas/`](../backend/schemas/) or within the route file.
2. Implement data retrieval or mutation in the appropriate repository under [`../backend/db/repositories/`](../backend/db/repositories/).
3. Add the route handler in the relevant module under [`../backend/api/routes/`](../backend/api/routes/).
4. Ensure the router is mounted in [`../backend/main.py`](../backend/main.py).
5. Document the endpoint specification in [`./API.md`](./API.md).

### Adding a New Surveillance Tool
1. Implement the tool function with strict parameter validation in [`../backend/agents/chat_agent.py`](../backend/agents/chat_agent.py) or [`../backend/agents/detection_agent.py`](../backend/agents/detection_agent.py).
2. Ensure the tool is strictly `SELECT`-only and enforces result set limits (`limit = min(limit, 25)`).
3. Register the tool function in the agent's tools dictionary.

---

## Troubleshooting & Common Pitfalls

### MySQL Reserved Keyword Error (`call`)
- **Symptom:** `ProgrammingError: (1064, "You have an error in your SQL syntax... near 'call'")`.
- **Cause:** `CALL` is a reserved SQL statement keyword in MySQL 8.0.
- **Fix:** Always wrap the table name in backticks: `` SELECT * FROM `call` WHERE id = %s ``.

### Unit Test Adapter Rule Violation
- **Symptom:** `RuntimeError: ABSOLUTE RULE 1 VIOLATION: Mock adapter 'RegexPiiRedactor' instantiated while ARGUS_PROVIDER_MODE='live'`.
- **Cause:** Running mock unit tests while `.env` has `ARGUS_PROVIDER_MODE=live`.
- **Fix:** Set the environment variable to mock mode during testing:
  ```powershell
  $env:ARGUS_PROVIDER_MODE="mock"; python -m pytest backend/tests/
  ```

### Python Import Resolution (`ModuleNotFoundError: No module named 'backend'`)
- **Symptom:** Running `pytest` directly results in module import failures.
- **Cause:** Python did not include the repository root in `sys.path`.
- **Fix:** Run pytest as a module: `python -m pytest ...`, or ensure `PYTHONPATH=.` is exported.

### WaveSurfer Audio Playback Fails on Range Headers
- **Symptom:** Audio waveform fails to seek or throws network errors in the browser.
- **Cause:** The server did not return `HTTP 206 Partial Content`.
- **Fix:** Ensure requests to `GET /api/calls/{call_id}/audio` include proper `Range: bytes=...` headers as handled in [`../backend/api/routes/calls.py`](../backend/api/routes/calls.py).

---

## Related Documents

- [Configuration Reference](./CONFIGURATION.md)
- [REST API Reference](./API.md)
- [Frontend Architecture](./FRONTEND.md)
- [Testing & Benchmark](./TESTING.md)
