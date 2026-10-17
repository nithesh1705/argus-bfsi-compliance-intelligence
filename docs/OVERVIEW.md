# ARGUS — Product Overview & Evidence Chain

An autonomous, explainable compliance intelligence platform for BFSI wealth management institutions.

[Back to documentation index](./INDEX.md) | [Next: System Architecture](./ARCHITECTURE.md)

---

## Table of Contents

- [The BFSI Compliance Problem](#the-bfsi-compliance-problem)
- [Target User Personas](#target-user-personas)
- [End-to-End Workflow](#end-to-end-workflow)
- [The Evidence Chain](#the-evidence-chain)
  - [Evidence Chain Schema](#evidence-chain-schema)
  - [Real Synthetic Example](#real-synthetic-example)
- [The Statutory Regulatory Corpus](#the-statutory-regulatory-corpus)
- [Glossary](#glossary)
- [Related Documents](#related-documents)

---

## The BFSI Compliance Problem

In the Indian Wealth Management and Banking, Financial Services, and Insurance (BFSI) sector, Asset Management Companies (AMCs) and banks manage hundreds of thousands of sales calls annually between Relationship Managers (RMs) and retail investors. Under Securities and Exchange Board of India (SEBI) and Association of Mutual Funds in India (AMFI) statutory frameworks, distributors and RMs must strictly adhere to statutory sales conduct:

1. **Guaranteed Return Prohibition:** Recommending market-linked securities (e.g. Equity, Small-Cap, Arbitrage funds) with explicit or implicit assurances of return, principal safety, or fixed yields violates SEBI (Mutual Funds) Regulations.
2. **Product Suitability Misalignment:** Pitching high-volatility, aggressive-growth equity schemes to conservative investors or customers with minimal investment experience without suitability assessments breaches SEBI circular directives.
3. **Missing Statutory Risk Disclosures:** Omitting scheme risk-o-meter disclosures, NAV market risk warnings, or volatility caveats violates AMFI sales ethics guidelines.
4. **Misleading Performance Claims:** Marketing past scheme returns without mandatory standardized disclosures.

### Traditional Monitoring Limitations

- **Sampling Blindspots:** Manual compliance teams can audit at most 1% to 3% of recorded audio calls due to bandwidth limits.
- **Human Inconsistency:** Human auditors interpret nuances differently, missing violations buried in 20-minute conversations.
- **Multilingual Code-Switching:** Indian sales calls frequently alternate between English, Hindi, Tamil, and Hinglish.
- **Lack of Verification:** Early AI solutions hallucinate regulatory clauses or generate ungrounded violation claims that do not withstand regulatory scrutiny.

ARGUS addresses these challenges by processing 100% of recorded calls in near-real-time, isolating speech segments, redacting statutory PII, retrieving binding regulatory circulars, running multi-agent forensic analysis with strict hard guardrails, and presenting an auditable Evidence Chain to compliance officers.

---

## Target User Personas

| Persona | Role in Platform | Key Responsibilities | Primary Interface |
|---|---|---|---|
| **Audit Officer (Compliance Analyst)** | Daily surveillance operator | Reviews flagged compliance cases, verifies the Evidence Chain, listens to linked audio segments, and marks cases reviewed or dismissed. | Operational Dashboard, Calls, Compliance Cases, AI Investigation |
| **Compliance Head (Supervisor)** | Escalation reviewer & reporter | Evaluates escalated cases requiring committee discretion, examines RM risk patterns, and generates authoritative compliance dossiers. | Compliance Cases (Escalations), RM Analytics, Report Dispatch |
| **System Administrator** | Platform operator | Monitors pipeline throughput, configures model parameters and confidence thresholds, updates master data rosters, and tracks APM health. | Executive Analytics, Master Data CRUD, Observability, Settings |

---

## End-to-End Workflow

The surveillance workflow operates autonomously from the moment an audio recording is uploaded to Cloud Storage until a compliance case is resolved:

```
[RM Sales Call Audio (.wav/.mp3)]
               │
               ▼
   [Cloud Storage (calls/incoming)]
               │  (GCS Object Finalize)
               ▼
    [Eventarc / Pub/Sub Push]
               │  (Authenticated OIDC)
               ▼
   [ARGUS Pipeline Runner (Cloud Run)]
         │
         ├─► 1. Ingestion Agent: Diarized transcription, language translation, role mapping (RM vs Customer)
         ├─► 2. Sensitive Data Protection: In-line PII redaction (PAN, Aadhaar, phone, card numbers)
         ├─► 3. Detection Agent: Pre-screening against catalog & customer profile; stages candidate findings
         ├─► 4. Retrieval Agent: Grounding search across 6,750+ authoritative regulatory chunks
         ├─► 5. Investigation Agent: Forensic reasoning enforcing 4 hard in-code guardrails
         ├─► 6. Atomic Persistence: Single MySQL transaction commits confirmed finding, case, and audit log
         └─► 7. Audio Archival: Object atomically moved to calls/archive/
               │
               ▼
  [Auditable Case Available in UI]
               │
   ┌───────────┴───────────┐
   ▼                       ▼
[Audit Officer Review]   [Committee Escalation]
 - Click-to-audio         - Risk dossier compilation
 - Quote verification     - Email compliance report
 - Mark Reviewed/Dismiss
```

Source implementations:
- Pipeline runner: [`../backend/ingestion/pipeline_runner.py`](../backend/ingestion/pipeline_runner.py)
- Event listener: [`../backend/api/routes/events.py`](../backend/api/routes/events.py)

---

## The Evidence Chain

The core operational artifact of ARGUS is the **Evidence Chain**. Rather than outputting a raw score or an unsupported classification, ARGUS synthesizes an unbroken, bidirectional verification trail that links the raw acoustic audio to the exact statutory paragraph:

```
Acoustic Audio Waveform
  │  (Exact millisecond interval: 14000ms - 22000ms)
  ▼
Verbatim Speech Excerpt
  │  (Original utterance & translated English text)
  ▼
Customer & Product Context
  │  (Customer risk profile vs Product risk classification)
  ▼
Authoritative Statutory Clause
  │  (Document name, clause number, page, permanent source URL)
  ▼
Forensic Rationale
  │  (Supporting evidence, contradicting evidence, reasoning)
  ▼
Audit Action & Resolution
     (Reviewer identity, action timestamp, immutable rationale)
```

### Evidence Chain Schema

Assembled by [`../backend/db/repositories/cases_repo.py`](../backend/db/repositories/cases_repo.py) and served via `GET /api/cases/{case_id}`:

| Field | Type | Description |
|---|---|---|
| `case_id` | string | Unique case identifier (e.g. `CASE-001`) |
| `call_id` | string | Originating call reference |
| `timestamp_start` / `timestamp_end` | integer | Audio segment boundaries in seconds |
| `quote_original` | string | Verbatim spoken excerpt (PII-redacted) |
| `quote_english` | string | English translation of the spoken excerpt |
| `category` | string | Statutory violation category (`GUARANTEED_RETURN`, etc.) |
| `severity` | string | Violation severity (`HIGH`, `MEDIUM`, `LOW`) |
| `confidence` | float | Model confidence score (0.0 to 1.0) |
| `regulation.citation_label` | string | Human-readable statutory label (e.g. `SEBI Code of Conduct Clause 2(b)`) |
| `regulation.chunk_id` | string | Unique primary key in `regulation_chunk_registry` |
| `regulation.source_url` | string | Direct URL to regulatory document on regulator portal |
| `evidence.supporting` | array | Facts supporting non-compliance |
| `evidence.contradicting` | array | Facts mitigating or challenging the finding |
| `evidence.rationale` | string | Structured legal-forensic explanation |
| `activity_log` | array | Chronological action history |

### Real Synthetic Example

From recorded benchmark call `CALL_RM001_CUST001_20260310_1030`:

```json
{
  "case_id": "CASE-RM001_CUST001_20260310_1030_1",
  "call_id": "CALL_RM001_CUST001_20260310_1030",
  "category": "GUARANTEED_RETURN",
  "severity": "HIGH",
  "confidence": 0.98,
  "timestamp_start": 14,
  "timestamp_end": 22,
  "quote_original": "Sir, this fund gives an 18% guaranteed return every year without any risk.",
  "quote_english": "Sir, this fund gives an 18% guaranteed return every year without any risk.",
  "regulation": {
    "citation_label": "SEBI Code of Conduct for Mutual Fund Distributors Clause 2(a)",
    "chunk_id": "SEBI_DIST_COND_2022_P03_C01",
    "source_url": "https://www.sebi.gov.in/legal/circulars/apr-2022/code-of-conduct-for-mutual-fund-distributors",
    "page_number": 3
  },
  "evidence": {
    "supporting": [
      "Speaker explicitly asserted an '18% guaranteed return'",
      "Target scheme is an equity small-cap mutual fund with High risk rating",
      "No disclaimer regarding market volatility or NAV fluctuation was provided"
    ],
    "contradicting": [],
    "rationale": "The Relationship Manager guaranteed an 18% return on a market-linked equity fund. Under SEBI regulations, mutual fund distributors are strictly prohibited from offering guaranteed returns or assurances of yield."
  }
}
```

---

## The Statutory Regulatory Corpus

The compliance intelligence engine is grounded against five authoritative regulatory documents indexed in Cloud SQL (`regulation_chunk_registry`) and stored in Cloud Storage (`argus-regulations`):

| Document Title | Issuing Body | Status | Chunks | Role in ARGUS |
|---|---|---|:---:|---|
| **SEBI (Mutual Funds) Regulations, 1996** (as amended Feb 2026) | SEBI | Current | 2,840 | Primary statutory framework governing mutual fund operations, scheme definitions, and disclosures. |
| **SEBI Master Circular for Mutual Funds** | SEBI | Current | 2,150 | Consolidated circular covering sales practices, advertising standards, and categorization. |
| **Revised Code of Conduct for Mutual Fund Distributors (April 2022)** | SEBI | Current | 385 | Specific operational prohibitions on mis-selling, suitability violations, and return guarantees. |
| **AMFI Code of Ethics (2026 Edition)** | AMFI | Current | 420 | Industry standard practices for relationship managers, distributors, and ethical customer interaction. |
| **SEBI (Mutual Funds) Regulations, 2026 Amendment** | SEBI | Current | 955 | Latest statutory updates on digital distribution, risk-o-meter disclosures, and compliance obligations. |

Source implementations:
- Chunk registry schema: [`../data/schemas/argus_mysql_ddl.sql`](../data/schemas/argus_mysql_ddl.sql)
- Extraction & indexing logic: [`../backend/indexing/`](../backend/indexing/)
- Ingestion runner: [`../scripts/ingest_regulations.py`](../scripts/ingest_regulations.py)

---

## Glossary

| Term | Definition |
|---|---|
| **AMFI** | Association of Mutual Funds in India — the industry trade association for mutual funds in India. |
| **Code-Switching** | Alternating between two or more languages (e.g. Hindi, English, Tamil) in a single sales conversation. |
| **Diarization** | Partitioning an audio stream into homogeneous segments according to speaker identity (e.g. Speaker 1 vs Speaker 2). |
| **DLP** | Sensitive Data Protection (formerly Cloud DLP) — Google Cloud API used to detect and redact sensitive identity data. |
| **Evidence Chain** | The unbroken provenance connecting raw audio timestamps, spoken quotes, customer context, and statutory citations. |
| **File Search** | Google Gemini Vector/RAG tool used to retrieve grounding clauses from regulatory corpus stores. |
| **Hard Guardrail** | Deterministic, non-bypassable programmatic validation enforced in Python code rather than LLM prompts. |
| **KYC** | Know Your Customer — mandatory customer identification process under Indian financial regulations. |
| **NAV** | Net Asset Value — the per-unit value of a mutual fund scheme based on the market value of its underlying assets. |
| **PII** | Personally Identifiable Information (PAN, Aadhaar number, phone number, debit/credit card numbers). |
| **RM** | Relationship Manager — banking or wealth management professional responsible for client advisory and sales. |
| **Risk-o-meter** | Standardized pictorial indicator mandated by SEBI to depict the risk level of a mutual fund scheme. |
| **SEBI** | Securities and Exchange Board of India — the apex statutory regulatory body for securities markets in India. |

---

## Related Documents

- [System Architecture](./ARCHITECTURE.md)
- [Agents & Guardrails](./AGENTS.md)
- [Data Model & Schema](./DATA_MODEL.md)
- [Screenshot Gallery](./GLIMPSE.md)
