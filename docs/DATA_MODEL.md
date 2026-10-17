# ARGUS — Data Model & Entity Relationship Schema

Comprehensive specification of the Cloud SQL for MySQL relational database schema, statutory chunk registry, and entity relationships.

[Back to documentation index](./INDEX.md) | [Next: API Reference](./API.md)

---

## Table of Contents

- [Entity Relationship Diagram](#entity-relationship-diagram)
- [Relational Tables Specification](#relational-tables-specification)
  - [1. Master Data Tables](#1-master-data-tables)
  - [2. Surveillance & Telephony Tables](#2-surveillance--telephony-tables)
  - [3. Forensic Pipeline & Audit Tables](#3-forensic-pipeline--audit-tables)
  - [4. Statutory Regulation Registry](#4-statutory-regulation-registry)
  - [5. Case Workflow & Audit Tables](#5-case-workflow--audit-tables)
  - [6. Platform Telemetry & Observability Tables](#6-platform-telemetry--observability-tables)
- [Finding-to-Case Lifecycle Mapping](#finding-to-case-lifecycle-mapping)
- [Regulation Chunk Registry & Citation Resolution](#regulation-chunk-registry--citation-resolution)
- [Gemini File Search Store Relationship](#gemini-file-search-store-relationship)
- [Related Documents](#related-documents)

---

## Entity Relationship Diagram

```mermaid
erDiagram
    rm ||--o{ `call` : conducts
    customer ||--o{ `call` : participates_in
    product ||--o{ `call` : discusses
    customer ||--o{ transaction : makes
    rm ||--o{ transaction : facilitates
    product ||--o{ transaction : purchases
    
    `call` ||--o{ transcript_segment : contains
    `call` ||--o{ candidate : flags
    `call` ||--o{ investigation : audits
    `call` ||--o{ finding : produces
    `call` ||--o{ compliance_case : generates
    `call` ||--o{ pipeline_run : tracks
    pipeline_run ||--o{ pipeline_stage_timing : times

    candidate ||--o| investigation : evaluates
    finding ||--|| compliance_case : materializes_as
    compliance_case ||--o{ case_activity_log : logs
    reviewer ||--o{ compliance_case : reviews
    
    regulation_chunk_registry ||--o{ finding : grounds
    regulatory_documents ||--o{ regulation_chunk_registry : indexes
    regulatory_authority ||--o{ regulatory_documents : promulgates
```

Source DDL file: [`../data/schemas/argus_mysql_ddl.sql`](../data/schemas/argus_mysql_ddl.sql)

---

## Relational Tables Specification

### 1. Master Data Tables

#### `rm` (Relationship Manager Master Roster)
Stores sales representatives subject to compliance monitoring.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `rm_id` | `VARCHAR(20)` | `PRIMARY KEY` | Unique RM identifier (e.g. `RM001`) |
| `full_name` | `VARCHAR(100)` | `NOT NULL` | Full legal name of the RM |
| `branch` | `VARCHAR(100)` | | Assigned banking or wealth management branch |
| `joined_date` | `DATE` | | Employment commencement date |
| `active` | `BOOLEAN` | `DEFAULT TRUE` | Active surveillance enrollment status |

#### `customer` (Client Investment Profile)
Maintains customer risk categorization and suitability metrics.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `customer_id` | `VARCHAR(20)` | `PRIMARY KEY` | Unique customer identifier (e.g. `CUST001`) |
| `full_name` | `VARCHAR(100)` | `NOT NULL` | Customer name |
| `mobile_number` | `VARCHAR(20)` | | Registered contact phone (masked in UI) |
| `risk_profile` | `VARCHAR(30)` | `NOT NULL` | Risk appetite: `Conservative`, `Moderate`, `Aggressive` |
| `investment_experience` | `VARCHAR(20)` | `NOT NULL` | Experience level: `Low`, `Medium`, `High` |
| `kyc_status` | `VARCHAR(20)` | `DEFAULT 'VERIFIED'` | Regulatory KYC verification status |

#### `product` (Mutual Fund Scheme Catalog)
Statutory catalog of schemes and their suitability rules.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `product_id` | `VARCHAR(20)` | `PRIMARY KEY` | Unique product scheme identifier |
| `product_name` | `VARCHAR(150)` | `NOT NULL` | Official scheme name |
| `risk_class` | `VARCHAR(30)` | `NOT NULL` | SEBI risk rating: `Low`, `Medium`, `High` |
| `suitable_risk_profiles` | `VARCHAR(100)` | `NOT NULL` | Comma-separated suitable customer profiles |
| `disclosure_requirements` | `TEXT` | | Mandatory scheme disclosure rules |

#### `transaction` (Historic Financial Transactions)
Historical investments used by agents to verify suitability history.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `transaction_id` | `VARCHAR(20)` | `PRIMARY KEY` | Unique transaction ID |
| `customer_id` | `VARCHAR(20)` | `FK -> customer.customer_id` | Purchasing customer |
| `rm_id` | `VARCHAR(20)` | `FK -> rm.rm_id` | Facilitating relationship manager |
| `product_id` | `VARCHAR(20)` | `FK -> product.product_id` | Transacted mutual fund scheme |
| `amount` | `DECIMAL(15,2)` | `NOT NULL` | Transaction monetary value in INR |
| `transaction_type` | `VARCHAR(30)` | `NOT NULL` | `PURCHASE`, `REDEMPTION`, `SIP` |
| `transaction_time` | `TIMESTAMP` | `NOT NULL` | Execution timestamp |

#### `reviewer` (Compliance Officers)
Authorized audit officers and compliance heads.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `reviewer_id` | `VARCHAR(20)` | `PRIMARY KEY` | Reviewer identity (e.g. `REV001`) |
| `full_name` | `VARCHAR(100)` | `NOT NULL` | Officer name |
| `role` | `VARCHAR(50)` | `NOT NULL` | Role: `Compliance Officer`, `Compliance Head` |
| `active` | `BOOLEAN` | `DEFAULT TRUE` | Active employment status |

#### `users` (System Users & JWT Auth)
Institutional authentication boundary managed by [`../backend/workflows/user_service.py`](../backend/workflows/user_service.py).

| Column | Type | Constraints | Description |
|---|---|---|---|
| `user_id` | `VARCHAR(64)` | `PRIMARY KEY` | Unique system user ID |
| `username` | `VARCHAR(50)` | `UNIQUE, NOT NULL` | Login username |
| `email` | `VARCHAR(100)` | `UNIQUE, NOT NULL` | Institutional email |
| `password_hash` | `VARCHAR(255)` | `NOT NULL` | Bcrypt password hash (12 salt rounds) |
| `role` | `VARCHAR(50)` | `DEFAULT 'Audit Officer'` | Application role: `Audit Officer`, `Admin` |
| `team` | `VARCHAR(50)` | `DEFAULT 'Compliance'` | Functional team |
| `access_level` | `VARCHAR(50)` | `DEFAULT 'All'` | Data segregation scope |
| `full_name` | `VARCHAR(100)` | `DEFAULT 'Audit Officer'` | Display name |
| `is_active` | `BOOLEAN` | `DEFAULT TRUE` | Active account toggle |
| `last_login_at` | `TIMESTAMP` | `NULL` | Most recent login timestamp |
| `created_at` / `updated_at` | `TIMESTAMP` | | Standard audit timestamps |

---

### 2. Surveillance & Telephony Tables

#### `` `call` `` (Call Audio Recordings)
Primary surveillance entity tracking audio files, statuses, and violation aggregates. Note: Backticks are mandatory in MySQL queries due to the reserved keyword.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `VARCHAR(64)` | `PRIMARY KEY` | Formatted call ID (e.g. `CALL_RM001_CUST001_20260310_1030`) |
| `rm_id` | `VARCHAR(20)` | `FK -> rm.rm_id` | Participating RM |
| `customer_id` | `VARCHAR(20)` | `FK -> customer.customer_id` | Participating customer |
| `product_id` | `VARCHAR(20)` | `NULL, FK -> product` | Primary product discussed |
| `gcs_uri_incoming` | `VARCHAR(500)` | | Initial incoming object path in GCS |
| `gcs_uri_archive` | `VARCHAR(500)` | | Permanent archived object path in GCS |
| `source_object_generation` | `VARCHAR(100)` | | Immutable GCS object generation integer for idempotency |
| `language` | `VARCHAR(30)` | `DEFAULT 'en'` | Dominant spoken language detected |
| `duration_s` | `DECIMAL(10,2)` | `DEFAULT 0.0` | Call duration in seconds |
| `status` | `VARCHAR(50)` | `DEFAULT 'RECEIVED'` | `RECEIVED`, `COMPLETED`, `FAILED`, `FAILED(validation)` |
| `speaker_mapping_method` | `VARCHAR(30)` | `DEFAULT 'llm'` | Role mapping method: `llm` or `heuristic_fallback` |
| `has_violation` | `BOOLEAN` | `DEFAULT FALSE` | True if one or more confirmed findings exist |
| `finding_count` | `INT` | `DEFAULT 0` | Total confirmed findings count |
| `severity` | `VARCHAR(10)` | `NULL` | Maximum severity observed (`HIGH`, `MEDIUM`, `LOW`) |
| `date_time` | `TIMESTAMP` | `NULL` | Call occurrence timestamp |
| `provider_used` | `VARCHAR(50)` | `DEFAULT 'mock'` | Provider executing analysis (`mock` or `vertex_ai`) |
| `is_mock` | `BOOLEAN` | `DEFAULT TRUE` | Offline mock data safety flag |

#### `transcript_segment` (Diarized Speech Segments)
Individual utterances with millisecond timestamps and PII-redacted text.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `segment_id` | `INT AUTO_INCREMENT` | `PRIMARY KEY` | Unique segment identifier |
| `call_id` | `VARCHAR(64)` | `FK -> call.id ON DELETE CASCADE` | Parent call reference |
| `idx` | `INT` | `NOT NULL` | Sequential utterance order (0, 1, 2...) |
| `speaker_label` | `VARCHAR(50)` | `NOT NULL` | Acoustic diarization label (`Speaker 1`) |
| `role` | `VARCHAR(20)` | `NOT NULL` | Assigned role: `RM` or `CUSTOMER` |
| `start_ms` | `INT` | `NOT NULL` | Utterance onset in milliseconds |
| `end_ms` | `INT` | `NOT NULL` | Utterance offset in milliseconds |
| `text_original` | `TEXT` | `NOT NULL` | Spoken regional text with PII tokens redacted |
| `text_english` | `TEXT` | `NOT NULL` | English translation with PII tokens redacted |
| `is_violation` | `BOOLEAN` | `DEFAULT FALSE` | Flagged as containing confirmed violation |

---

### 3. Forensic Pipeline & Audit Tables

#### `candidate` (Detection Pre-screening Output)
Candidate regulatory breaches flagged by the Detection Agent.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `candidate_id` | `VARCHAR(64)` | `PRIMARY KEY` | Unique candidate identifier |
| `call_id` | `VARCHAR(64)` | `FK -> call.id ON DELETE CASCADE` | Parent call reference |
| `category` | `VARCHAR(50)` | `NOT NULL` | Violation category |
| `severity_hint` | `VARCHAR(20)` | `NOT NULL` | Preliminary severity estimate |
| `start_ms` / `end_ms` | `INT` | `NOT NULL` | Estimated timestamp range in ms |
| `speaker` | `VARCHAR(20)` | `NOT NULL` | Uttering role (`RM`) |
| `quote_original` / `quote_english` | `TEXT` | `NOT NULL` | Verbatim excerpt from transcript |
| `rationale` | `TEXT` | `NOT NULL` | Detection Agent reasoning |
| `retrieval_queries` | `JSON` | | Suggested regulation queries |
| `retrieved_chunk_ids` | `JSON` | | Pre-screened regulation chunk IDs |

#### `investigation` (Forensic Audit Trail)
Audits the complete decision trail and token accounting per candidate.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `investigation_id` | `VARCHAR(64)` | `PRIMARY KEY` | Unique investigation audit ID |
| `candidate_id` | `VARCHAR(64)` | `NOT NULL` | Evaluated candidate reference |
| `call_id` | `VARCHAR(64)` | `FK -> call.id ON DELETE CASCADE` | Associated call reference |
| `outcome` | `VARCHAR(50)` | `NOT NULL` | `CONFIRMED`, `DISMISSED_NO_CITATION`, `DISMISSED_CITATION_MISMATCH`, `DISMISSED_OTHER`, `ESCALATE_FOR_REVIEW` |
| `reasoning` | `TEXT` | `NOT NULL` | Forensic legal reasoning |
| `model` | `VARCHAR(100)` | `NOT NULL` | Reasoning model ID |
| `token_count_prompt` / `token_count_completion` | `INT` | `DEFAULT 0` | LLM token usage metrics |
| `latency_ms` | `INT` | `DEFAULT 0` | LLM invocation latency |
| `raw_structured_output` | `JSON` | | Raw JSON output returned by model |

---

### 4. Statutory Regulation Registry

#### `regulatory_documents` (Statutory Document Catalog)
Master catalog of statutory regulations, circulars, and codes.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `document_id` | `VARCHAR(64)` | `PRIMARY KEY` | Unique document ID |
| `document_name` | `VARCHAR(255)` | `NOT NULL` | Human-readable title |
| `filename` | `VARCHAR(255)` | `NOT NULL` | Base filename in storage |
| `regulator` | `VARCHAR(50)` | `NOT NULL` | Authority: `SEBI`, `AMFI`, `RBI` |
| `document_type` | `VARCHAR(50)` | `DEFAULT 'REGULATION'` | `REGULATION`, `CIRCULAR`, `CODE_OF_CONDUCT` |
| `status` | `VARCHAR(20)` | `DEFAULT 'current'` | Status: `current`, `legacy` |
| `year` | `INT` | `DEFAULT 2026` | Enactment or revision year |
| `source_url` | `VARCHAR(500)` | `NOT NULL` | Official regulator portal URL |
| `storage_path` | `VARCHAR(500)` | | GCS bucket path |
| `file_size_bytes` | `INT` | | File size in bytes |
| `chunk_count` | `INT` | `DEFAULT 0` | Total registered statutory chunks |

#### `regulation_chunk_registry` (Authoritative Clause Chunks)
Atomic statutory paragraphs used for grounding and citations.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `chunk_id` | `VARCHAR(100)` | `PRIMARY KEY` | Deterministic chunk ID (e.g. `SEBI_DIST_COND_2022_P03_C01`) |
| `document_name` | `VARCHAR(255)` | `NOT NULL` | Document title |
| `clause` | `VARCHAR(255)` | | Section / Clause identifier |
| `citation_label` | `VARCHAR(255)` | `NOT NULL` | Formal citation label for display |
| `status` | `VARCHAR(20)` | `DEFAULT 'current'` | Current or legacy validity |
| `year` | `INT` | `NOT NULL` | Publication year |
| `effective_until` | `VARCHAR(50)` | `NULL` | Expiration date if superseded |
| `priority` | `INT` | `DEFAULT 1` | Retrieval weighting |
| `source_url` | `VARCHAR(500)` | `NOT NULL` | Permanent URL to source PDF |
| `page_number` | `INT` | `DEFAULT 1` | Page number in source document |
| `file_search_document_name` | `VARCHAR(255)` | `NULL` | Mapped Gemini File Search document name |
| `chunk_text` | `MEDIUMTEXT` | `NOT NULL` | Full verbatim statutory paragraph text |

#### `regulatory_authority` (Regulator Registry)
Statutory and industry regulatory bodies.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `authority_id` | `VARCHAR(50)` | `PRIMARY KEY` | Unique ID (e.g. `AUTH-SEBI`) |
| `name` | `VARCHAR(150)` | `NOT NULL` | Full legal name |
| `short_code` | `VARCHAR(20)` | `NOT NULL` | Acronym: `SEBI`, `AMFI`, `RBI`, `IRDAI` |
| `jurisdiction` | `VARCHAR(100)` | `DEFAULT 'India'` | Regulatory jurisdiction |
| `website_url` | `VARCHAR(255)` | | Official portal URL |
| `active` | `BOOLEAN` | `DEFAULT TRUE` | Active authority toggle |

---

### 5. Case Workflow & Audit Tables

#### `finding` (Confirmed Regulatory Findings)
Confirmed statutory violations verified by the Investigation Agent.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `finding_id` | `VARCHAR(64)` | `PRIMARY KEY` | Unique finding ID (e.g. `FND-001`) |
| `call_id` | `VARCHAR(64)` | `FK -> call.id ON DELETE CASCADE` | Source call reference |
| `investigation_id` | `VARCHAR(64)` | `NOT NULL` | Linked investigation audit ID |
| `regulation_chunk_id` | `VARCHAR(100)` | `FK -> regulation_chunk_registry.chunk_id` | Grounding statutory chunk |
| `citation_label` | `VARCHAR(255)` | `NOT NULL` | Human-readable statutory citation |
| `source_url` | `VARCHAR(500)` | `NOT NULL` | Regulator URL for citation |
| `page_number` | `INT` | `DEFAULT 1` | Page number of cited clause |
| `severity` | `VARCHAR(10)` | `NOT NULL` | `HIGH`, `MEDIUM`, `LOW` |
| `confidence` | `DECIMAL(5,4)` | `NOT NULL` | Numeric confidence score (0.0000 - 1.0000) |
| `category` | `VARCHAR(50)` | `NOT NULL` | Statutory category |
| `timestamp_start` / `timestamp_end` | `INT` | `NOT NULL` | Audio segment boundaries in seconds |
| `quote_original` / `quote_english` | `TEXT` | `NOT NULL` | Verbatim quote of violation |
| `evidence` | `JSON` | | Supporting, contradicting facts, and rationale |
| `provider_used` | `VARCHAR(50)` | `DEFAULT 'mock'` | Analysis provider |
| `model` | `VARCHAR(100)` | `NOT NULL` | Model executing finding |

#### `compliance_case` (Case Management Workflow)
Operational compliance cases managed by compliance teams.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `case_id` | `VARCHAR(64)` | `PRIMARY KEY` | Unique case ID (e.g. `CASE-001`) |
| `finding_id` | `VARCHAR(64)` | `FK -> finding.finding_id ON DELETE CASCADE` | Associated finding |
| `call_id` | `VARCHAR(64)` | `FK -> call.id ON DELETE CASCADE` | Parent call reference |
| `rm_id` | `VARCHAR(20)` | `FK -> rm.rm_id` | Flagged RM |
| `customer_id` | `VARCHAR(20)` | `FK -> customer.customer_id` | Involved customer |
| `category` | `VARCHAR(50)` | `NOT NULL` | Violation category |
| `severity` | `VARCHAR(10)` | `NOT NULL` | Severity assessment |
| `status` | `VARCHAR(20)` | `DEFAULT 'OPEN'` | State machine: `OPEN` or `RESOLVED` only |
| `escalated` | `BOOLEAN` | `DEFAULT FALSE` | True if escalated to compliance committee |
| `assigned_to` | `VARCHAR(20)` | `NULL, FK -> reviewer.reviewer_id` | Assigned reviewer ID |
| `resolution_notes` | `TEXT` | `NULL` | Officer's closing audit rationale |
| `resolution_type` | `VARCHAR(40)` | `NULL` | `CONFIRMED_ACTION_TAKEN`, `DISMISSED_FALSE_POSITIVE`, `ESCALATED_RESOLVED` |

#### `case_activity_log` (Reviewer Action Audit Trail)
Chronological, immutable audit trail of all actions on a case.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `log_id` | `INT AUTO_INCREMENT` | `PRIMARY KEY` | Log entry ID |
| `case_id` | `VARCHAR(64)` | `FK -> compliance_case.case_id ON DELETE CASCADE` | Target case |
| `action` | `VARCHAR(50)` | `NOT NULL` | `CREATED`, `STATUS_CHANGE`, `NOTE_ADDED`, `ASSIGNED`, `ESCALATED` |
| `actor` | `VARCHAR(20)` | `NOT NULL` | Reviewer ID or `SYSTEM` |
| `details` | `TEXT` | | Action narrative or notes |
| `timestamp` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` | Action occurrence time |

---

### 6. Platform Telemetry & Observability Tables

#### `pipeline_run` & `pipeline_stage_timing`
Latency tracking and error logging per stage.

- `pipeline_run`: Stores `run_id`, `call_id`, `trace_id`, `status` (`RECEIVED`, `COMPLETED`, `FAILED`), `source_object`, `start_time`, `end_time`, `total_duration_ms`, `error_details`.
- `pipeline_stage_timing`: Stores granular execution durations for `ingestion.transcribe_and_redact`, `detection.run`, `investigation.run`, and `archive.move`.

#### `provider_health`
Maintains operational health and latency for dependencies:
- `dependency_name`: `mysql`, `cloud_storage`, `vertex_ai`, `file_search`, `dlp`.
- `status`: `HEALTHY`, `DEGRADED`, `UNREACHABLE`.
- `latency_ms`, `details`, `last_checked_at`.

#### `app_settings`
Dynamic platform settings:
- `confidence_threshold`: Minimum confidence required to surface candidate findings.
- `active_ai_provider`: Selected provider mode.

---

## Finding-to-Case Lifecycle Mapping

Findings and cases maintain an atomic 1:1 operational binding:
1. When the Investigation Agent confirms a violation, `commit_confirmed_finding()` creates the `finding` record and the `compliance_case` record in the **same MySQL transaction**.
2. Case ID mirrors finding ID: `finding_id = FND-001` generates `case_id = CASE-001`.
3. If an audit officer resolves or dismisses a case, the finding remains permanently in `finding` for historical analytics, while `compliance_case.status` transitions to `RESOLVED`.
4. The dynamic property `needs_review` is computed at query time:
   ```sql
   status = 'OPEN' AND (severity = 'HIGH' OR escalated = TRUE)
   ```

---

## Regulation Chunk Registry & Citation Resolution

Every finding in ARGUS resolves its citation directly from `regulation_chunk_registry`:
- The Investigation Agent stores the exact primary key `regulation_chunk_id` in `finding.regulation_chunk_id`.
- The database enforces an explicit Foreign Key:
  ```sql
  FOREIGN KEY (regulation_chunk_id) REFERENCES regulation_chunk_registry(chunk_id)
  ```
- When `GET /api/cases/{case_id}` assembles the Evidence Chain, it joins `finding` with `regulation_chunk_registry` to yield:
  - Exact section/clause title (`citation_label`)
  - Permanent PDF download URL (`source_url`)
  - Exact page number (`page_number`)
  - Full statutory clause text (`chunk_text`)

---

## Gemini File Search Store Relationship

The Google Gemini File Search Store mirrors the Cloud SQL `regulation_chunk_registry`:
- Each PDF document in `RegulatoryDocs/` is pre-chunked into statutory sections using semantic clause boundaries (`backend/indexing/chunk.py`).
- Each chunk is registered in Cloud SQL with its `chunk_id` and uploaded to the Gemini File Search store (`ARGUS_FILE_SEARCH_STORE_NAME`).
- The attribute `file_search_document_name` in `regulation_chunk_registry` maps the Cloud SQL row to the vector store embedding document name, ensuring seamless bidirectional resolution during retrieval.

---

## Related Documents

- [System Architecture](./ARCHITECTURE.md)
- [Agents & Guardrails](./AGENTS.md)
- [API Reference](./API.md)
- [Security & Governance](./SECURITY.md)
