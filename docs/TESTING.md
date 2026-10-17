# ARGUS — Testing Strategy, Live Phase 2 Results & Benchmark

Comprehensive testing documentation covering offline mock suites, automated live Phase 2 cloud verification, and the three-way compliance intelligence benchmark.

[Back to documentation index](./INDEX.md) | [Next: Screenshot Gallery](./GLIMPSE.md)

---

## Table of Contents

- [Testing Strategy Overview](#testing-strategy-overview)
- [Test Inventory by Verification Area](#test-inventory-by-verification-area)
- [How to Run the Tests](#how-to-run-the-tests)
  - [1. Running the Offline Unit Suite](#1-running-the-offline-unit-suite)
  - [2. Running the Documentation Verification Suite](#2-running-the-documentation-verification-suite)
  - [3. Running the Live Phase 2 Cloud Suite](#3-running-the-live-phase-2-cloud-suite)
- [Real Phase 2 Live Results & Three-Way Benchmark](#real-phase-2-live-results--three-way-benchmark)
  - [Executive Comparative Benchmark Table](#executive-comparative-benchmark-table)
  - [Detailed 10-Call Evaluation Ledger](#detailed-10-call-evaluation-ledger)
  - [Call #9 Forensic Edge Case Analysis](#call-9-forensic-edge-case-analysis)
  - [Measured Pipeline Stage Latencies](#measured-pipeline-stage-latencies)
  - [Infrastructure Cost & Token Accounting](#infrastructure-cost--token-accounting)
- [Defects Discovered & Resolved During Phase 2](#defects-discovered--resolved-during-phase-2)
- [What Was Not Tested](#what-was-not-tested)
- [Related Documents](#related-documents)

---

## Testing Strategy Overview

ARGUS enforces a two-tier testing methodology to reconcile speed with live cloud fidelity:

1. **Tier 1: Offline Mock Suite (`backend/tests/`)**
   - 100% offline, zero network egress, zero cloud credentials required.
   - Executes against deterministic mock adapters (`MockRegulationRetriever`, `RegexPiiRedactor`, local simulated object store).
   - Designed for pre-commit developer workflows and continuous integration.
2. **Tier 2: Live Phase 2 Cloud Verification Suite (`tests/test_files/`)**
   - Executed live on Google Cloud Platform against real Vertex AI endpoints, Cloud SQL for MySQL, Cloud Storage buckets, Sensitive Data Protection, and Cloud Trace.
   - Evaluates real multilingual audio recordings across 10 standardized compliance scenarios.
   - Produces authoritative benchmark metrics and stage latency distributions recorded in [`../backend/benchmark/benchmark_report.md`](../backend/benchmark/benchmark_report.md) and [`../tests/results/`](../tests/results/).

---

## Test Inventory by Verification Area

The automated Phase 2 test suite covers thirteen distinct verification modules located in [`../tests/test_files/`](../tests/test_files/):

| Test Suite | Module File | Scope & Assertions |
|---|---|---|
| **T0: Environment** | [`test_t0_env.py`](../tests/test_files/test_t0_env.py) | Validates environment variables, Vertex AI location, project numbers, and model IDs. |
| **T1: Storage** | [`test_t1_storage.py`](../tests/test_files/test_t1_storage.py) | Verifies GCS bucket connectivity, object read/write, and simulated file paths. |
| **T2: Regulations** | [`test_t2_regulations.py`](../tests/test_files/test_t2_regulations.py) | Validates statutory PDF extraction, chunk registry population, and retrieval scoring. |
| **T3: Ingestion** | [`test_t3_ingestion.py`](../tests/test_files/test_t3_ingestion.py) | Asserts audio transcription, multilingual translation, speaker role mapping, and DLP redaction. |
| **T4: Detection** | [`test_t4_detection.py`](../tests/test_files/test_t4_detection.py) | Verifies candidate detection accuracy, quote alignment, and prompt injection isolation. |
| **T5: Investigation** | [`test_t5_investigation.py`](../tests/test_files/test_t5_investigation.py) | Enforces the four hard guardrails, citation verification, and single-transaction commit. |
| **T6: Pipeline** | [`test_t6_pipeline.py`](../tests/test_files/test_t6_pipeline.py) | End-to-end call processing reconciliation and benchmark execution. |
| **T7: API & Cases** | [`test_t7_api.py`](../tests/test_files/test_t7_api.py) | REST API endpoints, state machine 409 conflict responses, and Evidence Chain assembly. |
| **T8: AI Chat** | [`test_t8_chat.py`](../tests/test_files/test_t8_chat.py) | Conversational assistant, function tool calling, result capping, and read-only safety. |
| **T9: Observability** | [`test_t9_observability.py`](../tests/test_files/test_t9_observability.py) | OpenTelemetry span creation, trace correlation, and Cloud Trace deep links. |
| **T10: Security** | [`test_t10_security.py`](../tests/test_files/test_t10_security.py) | PII masking verification (PAN, Aadhaar), OIDC token verification on `/events/gcs`. |
| **T11: Frontend** | [`test_t11_frontend.py`](../tests/test_files/test_t11_frontend.py) | SPA routing, theme toggle persistence, WaveSurfer range streaming, and auth flow. |
| **T12: Resilience** | [`test_t12_resilience.py`](../tests/test_files/test_t12_resilience.py) | Error recording in `pipeline_run`, rate limit handling, and cost accounting. |

---

## How to Run the Tests

### 1. Running the Offline Unit Suite
Ensure your environment is set to mock mode before executing offline unit tests:

```bash
# Set provider mode to mock
export ARGUS_PROVIDER_MODE=mock
export ARGUS_GEMINI_TRANSCRIBE_MODEL=gemini-3.5-transcribe

# Run offline ingestion unit tests
python -m pytest backend/tests/test_ingestion_phase1d.py
```

### 2. Running the Documentation Verification Suite
Verify that all links, image paths, anchors, and project literals across the documentation comply with standards:

```bash
python scripts/check_docs_links.py
```

### 3. Running the Live Phase 2 Cloud Suite
> [!NOTE]
> The live suite requires active Google Cloud credentials and an initialized Cloud SQL instance with `ARGUS_PROVIDER_MODE=live`.

```bash
# Execute the full end-to-end benchmark suite
python backend/benchmark/run_benchmark.py
```

---

## Real Phase 2 Live Results & Three-Way Benchmark

The authoritative benchmark was executed against **10 Standardized Regulatory Compliance Calls** (3 High severity, 2 Medium severity, 2 Low severity, and 3 Clean calls) using live Vertex AI endpoints.

Results are recorded in [`../backend/benchmark/benchmark_report.md`](../backend/benchmark/benchmark_report.md) and [`../tests/results/`](../tests/results/).

### Executive Comparative Benchmark Table

| Metric | System 1: Keyword Baseline | System 2: Gemini Detection Only | System 3: Full ARGUS Pipeline |
|---|:---:|:---:|:---:|
| **Precision** | 100.0% | 66.7% | **85.7%** |
| **Recall** | 100.0% | 100.0% | **100.0%** |
| **F1 Score** | 100.0% | 80.0% | **92.3%** |
| **Accuracy** | 100.0% | 66.7% | **88.9%** |
| **True Positives (TP)** | 6 / 6 | 6 / 6 | **6 / 6** |
| **False Positives (FP)** | 0 | 3 | **1** |
| **False Negatives (FN)** | 0 | 0 | **0** |

> [!IMPORTANT]
> **Theoretical Recall Bound Directive:**
> Full-pipeline recall is fundamentally bounded by Detection recall. The Investigation Agent acts strictly as a forensic filter and never discovers candidates that Detection missed. In Phase 2, System 3 achieved 100% recall while successfully eliminating 67% of false positives generated by detection-only systems.

### Detailed 10-Call Evaluation Ledger

| Call ID | Ground Truth | System 1 (Keyword) | System 2 (Detection Only) | System 3 (Full ARGUS) |
|---|:---:|:---:|:---:|:---:|
| `CALL_RM001_CUST001_20260310_1030` | **HIGH** | VIOLATION | VIOLATION | **VIOLATION (CONFIRMED)** |
| `CALL_RM001_CUST004_20260405_1145` | **MEDIUM** | VIOLATION | VIOLATION | **VIOLATION (CONFIRMED)** |
| `CALL_RM002_CUST002_20260318_0915` | **HIGH** | VIOLATION | VIOLATION | **VIOLATION (CONFIRMED)** |
| `CALL_RM002_CUST005_20260422_1400` | **CLEAN** | CLEAN | VIOLATION (FP) | **CLEAN (DISMISSED)** |
| `CALL_RM003_CUST003_20260212_1620` | **HIGH** | VIOLATION | VIOLATION | **VIOLATION (CONFIRMED)** |
| `CALL_RM003_CUST003_20260630_1330` | **LOW** | VIOLATION | VIOLATION | **VIOLATION (CONFIRMED)** |
| `CALL_RM004_CUST004_20260228_1050` | **CLEAN** | CLEAN | VIOLATION (FP) | **CLEAN (DISMISSED)** |
| `CALL_RM004_CUST002_20260701_0930` | **MEDIUM** | VIOLATION | VIOLATION | **VIOLATION (CONFIRMED)** |
| `CALL_RM005_CUST005_20260319_1200` | **LOW** | VIOLATION | VIOLATION | **VIOLATION (CONFIRMED)** |
| `CALL_RM005_CUST001_20260815_1615` | **CLEAN** | CLEAN | VIOLATION (FP) | **VIOLATION (FP)** |

### Call #9 Forensic Edge Case Analysis
- **Call ID:** `CALL_RM005_CUST005_20260319_1200`
- **Context:** An ambiguous suitability scenario involving an investor with a Moderate risk profile and Low investment experience.
- **Outcome:** Either `CONFIRMED-LOW` or `DISMISSED` is defensible under SEBI guidance. System 3 confirmed the case as Low severity, preserving it for human compliance officer adjudication.

### Measured Pipeline Stage Latencies

Extracted directly from recorded live `pipeline_stage_timing` entries:

| Pipeline Stage | Mean Duration (ms) | Median Duration (ms) | Min (ms) | Max (ms) | Sample Count |
|---|:---:|:---:|:---:|:---:|:---:|
| `archive.move` | 2,433.5 ms | 2,387.5 ms | 2,254 ms | 2,970 ms | 10 |
| `detection.run` | 29,712.2 ms | 24,037.0 ms | 16,598 ms | 63,116 ms | 11 |
| `ingestion.transcribe_and_redact` | 64,027.4 ms | 59,147.5 ms | 51,417 ms | 108,208 ms | 12 |
| `investigation.run` | 66,290.7 ms | 44,481.0 ms | 16,576 ms | 288,174 ms | 10 |
| **Total End-to-End** | **158,868 ms (158.9s)** | **130,366.0 ms** | **90,046 ms** | **464,384 ms** | **12** |

### Infrastructure Cost & Token Accounting
From test suite T12 ([`../tests/test_files/test_t12_resilience.py`](../tests/test_files/test_t12_resilience.py)):
- Total call audio duration transcribed: ~2,455 seconds (~40.9 minutes).
- Estimated Vertex AI and DLP processing cost for the full benchmark: **$0.23 USD**.
- Running cost was verified to be well below the $10.00 USD safety threshold.

---

## Defects Discovered & Resolved During Phase 2

1. **MySQL Reserved Keyword `call`:**
   - *Defect:* Direct SQL queries (`SELECT COUNT(*) FROM call`) failed due to `CALL` being a reserved word in MySQL 8.0.
   - *Fix:* Wrapped all references in backticks (`` `call` ``) across repositories and test files.
2. **Column Name Mismatch (`duration_seconds` vs `duration_s`):**
   - *Defect:* Cost accounting tests originally queried `duration_seconds` which did not exist on `` `call` ``.
   - *Fix:* Updated query to reference the schema-accurate `duration_s` column.
3. **Frontend Reverse Proxy Login Routing:**
   - *Defect:* Direct login requests through the frontend Nginx container required proper `/api/` upstream proxying to avoid CORS pre-flight stalls.
   - *Fix:* Configured Nginx proxy directives in [`../frontend/Dockerfile`](../frontend/Dockerfile) and verified via `test_live_login.py`.

---

## What Was Not Tested

1. **Multi-Region Cloud SQL High Availability:** Testing utilized a single `db-f1-micro` instance without failover replication to minimize costs during the hackathon evaluation window.
2. **Model Armor Prompt Screening:** Tier 3 Model Armor screening was left disabled (`ARGUS_MODEL_ARMOR_ENABLED=false`).
3. **Concurrent 1,000+ Call Load Tests:** Ingestion was tested up to 12 sequential calls; large-scale distributed load tests remain for enterprise staging.

---

## Related Documents

- [System Architecture](./ARCHITECTURE.md)
- [Agents & Hard Guardrails](./AGENTS.md)
- [Observability Architecture](./OBSERVABILITY.md)
- [Roadmap & Known Limitations](./ROADMAP.md)
