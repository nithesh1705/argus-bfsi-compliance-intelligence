# ARGUS — System Architecture & Data Flow

Detailed architectural specification, distributed event flow, sequence diagrams, and design decisions for the ARGUS platform.

[Back to documentation index](./INDEX.md) | [Next: Technology Stack](./TECH_STACK.md)

---

## Table of Contents

- [System Context](#system-context)
- [Component Architecture](#component-architecture)
- [Pipeline Flowchart](#pipeline-flowchart)
- [Sequence Diagrams](#sequence-diagrams)
  - [Call Processing Sequence](#call-processing-sequence)
  - [AI Investigation Chat Sequence](#ai-investigation-chat-sequence)
- [Event Ingestion Path](#event-ingestion-path)
- [Idempotency & State Machine](#idempotency--state-machine)
  - [Idempotency Design](#idempotency-design)
  - [Pipeline State Machine](#pipeline-state-machine)
- [Failure Handling & Resiliency](#failure-handling--resiliency)
- [Design Decisions & Trade-Offs](#design-decisions--trade-offs)
- [Related Documents](#related-documents)

---

## System Context

ARGUS operates as an event-driven compliance intelligence engine hosted on Google Cloud Platform, bridging raw acoustic telephony streams with institutional compliance casework:

```mermaid
flowchart TB
    Telephony[Telephony & Call Recorder] -->|Upload .wav/.mp3| GCS_In[Cloud Storage: calls/incoming]
    GCS_In -->|Object Finalize Event| Eventarc[Eventarc Trigger]
    Eventarc -->|OIDC Push| PubSub[Pub/Sub Push Topic]
    PubSub -->|POST /events/gcs| CloudRun[ARGUS Backend API on Cloud Run]
    
    CloudRun <-->|Transcription, LLM Reasoning| Vertex[Vertex AI: Gemini Models]
    CloudRun <-->|PII De-identification| DLP[Sensitive Data Protection API]
    CloudRun <-->|Statutory Regulation Corpus| GCS_Reg[Cloud Storage: argus-regulations]
    CloudRun <-->|Relational Data & Citations| MySQL[(Cloud SQL for MySQL)]
    CloudRun -->|Distributed Spans| Trace[Google Cloud Trace]
    CloudRun -->|Structured Logs| Logging[Google Cloud Logging]
    
    Frontend[ARGUS React Frontend on Cloud Run] <-->|REST API + Bearer JWT| CloudRun
    ComplianceUser[Audit Officer / Compliance Head] <-->|Browser UI| Frontend
```

---

## Component Architecture

The application is decomposed into specialized functional layers with clean separation between transport, domain orchestration, and external adapters:

```mermaid
graph TB
    subgraph Frontend["Frontend Layer (React 18 + Vite)"]
        UI_Dash[Operational & Admin Dashboards]
        UI_Audio[WaveSurfer Audio Player]
        UI_Chain[Evidence Chain Inspector]
        UI_Chat[AI Investigation Assistant]
        UI_Theme[Dual-Theme Engine + Owl Toggle]
    end

    subgraph API["Transport Layer (FastAPI)"]
        R_Events["/events/gcs & /api/pipeline/process-now"]
        R_Cases["/api/cases/* (Evidence Chain)"]
        R_Calls["/api/calls/* (HTTP 206 Audio Streaming)"]
        R_Chat["/api/chat/* (SELECT-only Assistant)"]
        R_Reg["/api/regulations/* & /api/documents/*"]
        R_Admin["/api/admin/* (Master Data CRUD)"]
        R_System["/api/system/health & /api/system/diagnostics"]
    end

    subgraph Pipeline["Orchestration Layer (Pipeline Runner)"]
        Runner[Pipeline Runner Engine]
        IngestAgent[Ingestion Agent]
        DetectAgent[Detection Agent]
        InvestAgent[Investigation Agent]
        Guardrails[Hard Guardrails Filter]
    end

    subgraph Adapters["Infrastructure Adapters Layer"]
        Ad_Store[ObjectStore: GCS / Local]
        Ad_Trans[Transcriber: Gemini Audio / Mock]
        Ad_LLM[LLM Client: Vertex AI / Mock]
        Ad_Ret[Retriever: Chunk Registry / File Search]
        Ad_DLP[PII Redactor: Sensitive Data Protection]
        Ad_DB[Database Manager: Cloud SQL Connector]
    end

    Frontend --> API
    API --> Pipeline
    Pipeline --> Adapters
```

Source implementations:
- Router: [`../backend/main.py`](../backend/main.py)
- Configuration: [`../backend/core/config.py`](../backend/core/config.py)
- Adapters: [`../backend/adapters/`](../backend/adapters/)

---

## Pipeline Flowchart

The surveillance pipeline processes an uploaded call through sequential stages, writing granular timing telemetry at each step:

```mermaid
flowchart TD
    Start([Audio Object Finalized]) --> IdempCheck{Already Processed?<br>Object + Generation}
    IdempCheck -- Yes --> Skip([Exit: ALREADY_PROCESSED])
    IdempCheck -- No --> ParseName[Parse & Validate Filename<br>RM_id, CUST_id, DateTime]
    
    ParseName -- Invalid --> FailCall[Record FAILED validation<br>Status in DB]
    ParseName -- Valid --> CreateRec[Create Call Record<br>Status: RECEIVED]
    
    CreateRec --> StageIngest[Stage 1: Ingestion<br>Audio Transcription & Diarization]
    StageIngest --> StageTrans[Stage 2: Translation & Role Mapping<br>Gemini 2.5 Flash + Custom Product Vocab]
    StageTrans --> StageDLP[Stage 3: PII Redaction<br>Sensitive Data Protection API]
    StageDLP --> SaveSegs[Save Redacted Segments<br>to transcript_segment table]
    
    SaveSegs --> StageDetect[Stage 4: Detection Agent<br>Pre-screening against catalog & history]
    StageDetect --> StageRetr[Stage 5: Retrieval Agent<br>Grounding against regulation chunks]
    StageRetr --> StageInvest[Stage 6: Investigation Agent<br>Forensic analysis & Hard Guardrails]
    
    StageInvest --> GuardrailCheck{Guardrails Passed?<br>Citations Valid?}
    GuardrailCheck -- No --> AuditDismiss[Record Dismissal Audit<br>in investigation table]
    GuardrailCheck -- Yes --> AtomicCommit[Atomic Commit in Single Transaction:<br>finding + compliance_case + case_activity_log]
    
    AuditDismiss --> StageArchive[Stage 7: Archive Move<br>Move object to calls/archive/]
    AtomicCommit --> StageArchive
    
    StageArchive --> Finalize[Mark Call COMPLETED<br>Record Pipeline Timings]
    Finalize --> End([Ready for Review])
```

---

## Sequence Diagrams

### Call Processing Sequence

```mermaid
sequenceDiagram
    autonumber
    actor Storage as GCS calls/incoming
    participant Eventarc as Eventarc / PubSub
    participant EventsAPI as backend/api/routes/events.py
    participant Runner as backend/ingestion/pipeline_runner.py
    participant Ingestion as backend/ingestion/ingestion_agent.py
    participant Detection as backend/agents/detection_agent.py
    participant Retriever as backend/adapters/retriever.py
    participant Investigation as backend/agents/investigation_agent.py
    participant DB as Cloud SQL for MySQL
    participant GCSArchive as GCS calls/archive

    Storage->>Eventarc: Object Finalize (RM001_CUST001...wav)
    Eventarc->>EventsAPI: POST /events/gcs (Pub/Sub Push + OIDC)
    EventsAPI->>EventsAPI: Verify OIDC Bearer Token
    EventsAPI->>Runner: BackgroundTask: run_pipeline_for_object()
    EventsAPI-->>Eventarc: HTTP 200 (ACK)

    Runner->>DB: Check idempotency (object + generation)
    Runner->>DB: INSERT call (RECEIVED) & pipeline_run
    
    Runner->>Ingestion: process_audio_ingestion()
    Ingestion->>Ingestion: Transcribe audio (gemini-3.5-transcribe)
    Ingestion->>Ingestion: Role mapping & translation (gemini-2.5-flash)
    Ingestion->>Ingestion: Redact PII (Sensitive Data Protection API)
    Ingestion->>DB: INSERT transcript_segment rows
    
    Runner->>Detection: run_detection(call_id)
    Detection->>DB: Fetch customer profile & product catalog
    Detection->>DB: INSERT candidate rows
    
    Runner->>Investigation: run_investigation_for_call(call_id)
    loop Each Staged Candidate
        Investigation->>Retriever: search_regulations(category_query)
        Retriever->>DB: Query regulation_chunk_registry
        Retriever-->>Investigation: List of RetrievedPassage
        Investigation->>Investigation: Apply Guardrail 1 (No citations?)
        Investigation->>Investigation: LLM forensic evaluation (gemini-3.5-flash)
        Investigation->>Investigation: Apply Guardrail 2 (Citation mismatch?)
        Investigation->>Investigation: Apply Guardrail 3 (HIGH severity checks)
        Investigation->>Investigation: Apply Guardrail 4 (Quote alignment)
        opt If Confirmed
            Investigation->>DB: Single Transaction: commit_confirmed_finding()<br>(finding + compliance_case + activity_log)
        end
        Investigation->>DB: INSERT investigation audit row
    end

    Runner->>GCSArchive: Move audio object from incoming/ to archive/
    Runner->>DB: UPDATE call status = COMPLETED, archive_uri
    Runner->>DB: UPDATE pipeline_run status = COMPLETED, duration_ms
```

### AI Investigation Chat Sequence

```mermaid
sequenceDiagram
    autonumber
    actor Officer as Compliance Officer
    participant ChatUI as Frontend AI Investigation Page
    participant ChatAPI as backend/api/routes/chat.py
    participant ChatAgent as backend/agents/chat_agent.py
    participant Vertex as Vertex AI (Gemini Flash)
    participant DB as Cloud SQL for MySQL

    Officer->>ChatUI: Submits question ("Did RM001 guarantee returns?")
    ChatUI->>ChatAPI: POST /api/chat/message (message, history, session_id)
    ChatAPI->>ChatAgent: process_chat_message()
    
    ChatAgent->>Vertex: Generate with function tools (search_calls, search_findings, etc.)
    
    loop Max 5 iterations (Max 8 tool calls)
        Vertex-->>ChatAgent: ToolCall: search_findings_summary(category='GUARANTEED_RETURN')
        ChatAgent->>DB: SELECT from finding table (capped at 25 rows)
        DB-->>ChatAgent: Row results
        ChatAgent->>Vertex: Return ToolOutput to LLM
    end
    
    Vertex-->>ChatAgent: Final grounded response text
    ChatAgent->>ChatAgent: Assemble grounded_results strictly from tool outputs
    ChatAgent-->>ChatAPI: Response payload (reply, tools_called, grounded_results)
    ChatAPI-->>ChatUI: HTTP 200 JSON
    ChatUI-->>Officer: Render grounded answer with clickable citations
```

---

## Event Ingestion Path

The cloud ingestion pathway guarantees decoupled, near-real-time ingestion while preventing request timeouts:

1. **Ingress Upload:** Audio files are dropped into `gs://<YOUR_CALLS_BUCKET>/calls/incoming/`.
2. **Event Notification:** GCS triggers a Google Eventarc `google.cloud.storage.object.v1.finalized` event.
3. **Pub/Sub Invocation:** Eventarc pushes the event through a dedicated Pub/Sub topic to `https://<YOUR_BACKEND_URL>/events/gcs`.
4. **OIDC Verification:** The backend verifies that the HTTP request Bearer token was signed by Google Cloud and originates from the authorized invoker service account (`argus-eventarc-invoker-sa@<YOUR_GCP_PROJECT_ID>.iam.gserviceaccount.com`).
5. **Immediate Acknowledgment:** The endpoint acknowledges receipt (`HTTP 200 {"status": "ACK_SCHEDULED"}`) within 50 ms to prevent Pub/Sub redelivery storms.
6. **Background Task Execution:** The actual multi-stage analysis executes within a FastAPI `BackgroundTask` worker thread.

Source implementation: [`../backend/api/routes/events.py`](../backend/api/routes/events.py)

---

## Idempotency & State Machine

### Idempotency Design

Duplicate event deliveries can occur in distributed Pub/Sub systems. ARGUS prevents redundant processing through three explicit safeguards:

1. **Generation-Keyed Deduplication:** Every GCS object finalize event carries an immutable `generation` integer. Before pipeline execution, the runner checks:
   ```sql
   SELECT id, status FROM `call`
   WHERE gcs_uri_incoming LIKE %s AND source_object_generation = %s
   ```
   If a completed record exists, the event is acknowledged and immediately skipped.
2. **Deterministic Primary Keys:** Entity keys are deterministically generated from call IDs and candidate indices (e.g. `CAND-RM001_CUST001_20260310_1030_1`, `FND-...`, `CASE-...`).
3. **Idempotent MySQL Upserts:** Inserts into `candidate`, `investigation`, and `finding` utilize `ON DUPLICATE KEY UPDATE` to avoid duplicate primary key collisions.

### Pipeline State Machine

A call progresses through strict state transitions recorded in the database:

```
                  ┌──────────────────────┐
                  │       RECEIVED       │
                  └──────────┬───────────┘
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
   [Validation Failed]               [Validation Passed]
            │                                 │
            ▼                                 ▼
┌──────────────────────┐          ┌──────────────────────┐
│  FAILED(validation)  │          │      PROCESSING      │
└──────────────────────┘          └──────────┬───────────┘
                                             │
                             ┌───────────────┴───────────────┐
                             ▼                               ▼
                  [Pipeline Stage Error]          [All Stages Complete]
                             │                               │
                             ▼                               ▼
                  ┌──────────────────────┐        ┌──────────────────────┐
                  │        FAILED        │        │      COMPLETED       │
                  └──────────────────────┘        └──────────────────────┘
```

The database tracks transitions in two tables:
- `` `call`.status ``: High-level lifecycle state (`RECEIVED`, `COMPLETED`, `FAILED`, `FAILED(validation)`).
- `pipeline_run.status` & `pipeline_stage_timing`: Sub-second timing for every constituent step.

---

## Failure Handling & Resiliency

1. **Pub/Sub Poison Pill Protection:** If an uploaded audio file is corrupted or carries an invalid filename pattern, the pipeline records a `FAILED(validation)` entry and acknowledges the Pub/Sub message. This stops repeated retries and prevents event-loop exhaustion.
2. **Transient Model Rate Limits:** Vertex AI QPM limits are mitigated by a 1.0-second inter-candidate sleep interval in `backend/agents/investigation_agent.py`.
3. **Storage Fallback:** If Cloud Storage is temporarily degraded, local disk backups under `data/storage/` provide continuity during offline mock execution.
4. **State Machine 409 Conflict Safety:** Concurrent compliance officer actions (such as attempting to dismiss a case that another officer already reviewed) trigger structured `HTTP 409 Conflict` exceptions, preserving audit trail integrity.

---

## Design Decisions & Trade-Offs

| Decision | Chosen Approach | Alternative Considered | Rationale & Trade-Off |
|---|---|---|---|
| **Guardrail Enforcement** | In-code Python logic (`investigation_agent.py`) | Relying solely on LLM system prompt instructions | System prompts can be bypassed or misinterpreted; deterministic Python assertions guarantee 0% hallucinated citations. |
| **Retrieval Strategy** | Direct Cloud SQL Chunk Registry + File Search | External vector database (Pinecone, Milvus, Qdrant) | Embedding the statutory chunk registry directly into Cloud SQL MySQL eliminated an external service dependency, enabling ACID-compliant foreign keys between findings and statutory chunks. |
| **Model Distribution** | Vertex AI `gemini-3.5-flash` for reasoning; `gemini-2.5-flash` for speaker roles | Single model across all tasks | `gemini-2.5-flash` provides rapid, accurate speaker identification and role assignment; `gemini-3.5-flash` handles complex legal reasoning and multi-turn chat. |
| **Persistence Transaction** | Single ACID MySQL transaction for finding, case, and audit log | Multi-step individual REST/DB writes | Guarantees that a confirmed finding can never exist without a corresponding compliance case and audit log entry. |
| **Dual Provider Adapters** | Abstract Base Classes with `Mock` and `Live` adapters | Mocking at HTTP/network boundary | Enables 100% offline development, test automation, and CI validation without requiring Google Cloud credentials or incurring API costs. |

---

## Related Documents

- [Product Overview](./OVERVIEW.md)
- [Technology Stack](./TECH_STACK.md)
- [Agents & Guardrails](./AGENTS.md)
- [Observability Architecture](./OBSERVABILITY.md)
- [Security & Governance](./SECURITY.md)
