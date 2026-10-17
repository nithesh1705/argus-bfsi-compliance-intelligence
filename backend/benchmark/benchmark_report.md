# ARGUS — Three-Way Compliance Intelligence Benchmark

**Environment:** LIVE GCP (Vertex AI)  
**Evaluation Models:** `gemini-2.5-flash` (Detection & Investigation), `gemini-2.5-flash` (Ingestion)  
**Corpus Evaluated:** 10 Standardized Regulatory Compliance Calls (3 HIGH, 2 MEDIUM, 2 LOW, 3 CLEAN)  

---

## 1. Executive Summary & Comparative Performance

| Evaluation Metric | System 1: Keyword Baseline | System 2: Gemini Detection Only | System 3: Full ARGUS Pipeline |
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
> Full-pipeline recall is fundamentally bounded by Detection recall. The Investigation Agent acts strictly as a forensic filter and never discovers candidates that Detection missed.

---

## 2. Call #9 Analysis (Ambiguous Suitability Case)

- **Call ID:** `CALL_RM005_CUST005_20260319_1200`
- **Context:** Ambiguous suitability evaluation (Moderate risk profile, Low investment experience).
- **Methodological Note:** A genuine judgment call; either CONFIRMED-LOW or DISMISSED is acceptable. Excluded from strict precision/recall.
- **System 1 (Keyword Baseline):** Fired candidate? `True`
- **System 2 (Gemini Detection):** Candidate staged? `True`
- **System 3 (Full Pipeline):** Final outcome: `CONFIRMED`

---

## 3. Real Pipeline Stage Latencies (from `pipeline_stage_timing`)

| Pipeline Stage | Mean Duration (ms) | Median Duration (ms) | Min (ms) | Max (ms) | Sample Count |
|---|:---:|:---:|:---:|:---:|:---:|
| `archive.move` | 2433.5 | 2387.5 | 2254 | 2970 | 10 |
| `detection.run` | 29712.2 | 24037 | 16598 | 63116 | 11 |
| `ingestion.transcribe_and_redact` | 64027.4 | 59147.5 | 51417 | 108208 | 12 |
| `investigation.run` | 66290.7 | 44481.0 | 16576 | 288174 | 10 |
| `end_to_end` | 158868 | 130366.0 | 90046 | 464384 | 12 |

---

## 4. Detailed Per-Call Evaluation Ledger

| Call ID | Ground Truth | System 1 (Rule Baseline) | System 2 (Detection Only) | System 3 (Full ARGUS) |
|---|:---:|:---:|:---:|:---:|
| `CALL_RM001_CUST001_20260310_1030` | **HIGH** | VIOLATION | VIOLATION | **VIOLATION** |
| `CALL_RM001_CUST004_20260405_1145` | **MEDIUM** | VIOLATION | VIOLATION | **VIOLATION** |
| `CALL_RM002_CUST002_20260318_0915` | **HIGH** | VIOLATION | VIOLATION | **VIOLATION** |
| `CALL_RM002_CUST005_20260422_1400` | **CLEAN** | CLEAN | VIOLATION | **CLEAN** |
| `CALL_RM003_CUST003_20260212_1620` | **HIGH** | VIOLATION | VIOLATION | **VIOLATION** |
| `CALL_RM003_CUST003_20260630_1330` | **LOW** | VIOLATION | VIOLATION | **VIOLATION** |
| `CALL_RM004_CUST004_20260228_1050` | **CLEAN** | CLEAN | VIOLATION | **CLEAN** |
| `CALL_RM004_CUST002_20260701_0930` | **MEDIUM** | VIOLATION | VIOLATION | **VIOLATION** |
| `CALL_RM005_CUST005_20260319_1200` | **LOW** | VIOLATION | VIOLATION | **VIOLATION** |
| `CALL_RM005_CUST001_20260815_1615` | **CLEAN** | CLEAN | VIOLATION | **VIOLATION** |
