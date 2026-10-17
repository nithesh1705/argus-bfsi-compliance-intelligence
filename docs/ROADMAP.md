# ARGUS — Known Limitations & Strategic Roadmap

Honest assessment of documented operational limitations, Phase 2 test observations, and prioritized architectural roadmap milestones.

[Back to documentation index](./INDEX.md) | [Back to Root README](../README.md)

---

## Table of Contents

- [Documented Limitations & Forensic Boundaries](#documented-limitations--forensic-boundaries)
  - [1. Theoretical Recall Bound Directive](#1-theoretical-recall-bound-directive)
  - [2. Borderline Suitability Adjudication](#2-borderline-suitability-adjudication)
  - [3. Code-Switching & Acoustic Crosstalk](#3-code-switching--acoustic-crosstalk)
- [Open Defects & Operational Caveats](#open-defects--operational-caveats)
- [Strategic Product Roadmap](#strategic-product-roadmap)
  - [Phase 3: Enterprise Hardening (Next Steps)](#phase-3-enterprise-hardening-next-steps)
  - [Phase 4: Unimplemented Tier-3 Vision Features](#phase-4-unimplemented-tier-3-vision-features)
- [Related Documents](#related-documents)

---

## Documented Limitations & Forensic Boundaries

Honesty over polish is a core design value in ARGUS. Based on recorded results from the automated Phase 2 test suite on Google Cloud ([`../backend/benchmark/benchmark_report.md`](../backend/benchmark/benchmark_report.md)), the following architectural boundaries are formally documented:

### 1. Theoretical Recall Bound Directive
Full-pipeline recall is fundamentally bounded by Detection Agent recall. The Investigation Agent functions strictly as a forensic filter and never discovers candidates that Detection missed:

$$\text{Recall}_{\text{Pipeline}} \le \text{Recall}_{\text{Detection}}$$

While System 3 (Full ARGUS Pipeline) achieved **100.0% recall** on the standardized 10-call benchmark, any potential false negative at the pre-screening stage will not be recovered during investigation.

### 2. Borderline Suitability Adjudication
In Call #9 (`CALL_RM005_CUST005_20260319_1200`), an investor possessed a `Moderate` risk appetite but `Low` investment experience. Determining whether an equity hybrid fund is suitable for this specific combination is an ambiguous judgment call under SEBI regulations. 

ARGUS confirmed the violation with a `LOW` severity hint rather than unilaterally dismissing it, ensuring human compliance officers review the decision. Fully automated adjudication of borderline risk profiles remains a limitation.

### 3. Code-Switching & Acoustic Crosstalk
The platform handles conversational code-switching (Hindi/English/Tamil). However, when relationship managers and customers speak simultaneously over poor telephony connections, acoustic diarization accuracy degrades. While custom vocabulary injection preserves scheme names, overlapping audio segments can occasionally lead to ambiguous speaker role boundaries.

---

## Open Defects & Operational Caveats

The following items were noted during live testing:

1. **MySQL Reserved Keyword Quoting:** All raw SQL queries must escape `` `call` `` with backticks. Standard ORM queries are unaffected, but custom SQL scripts must observe this syntax rule.
2. **Schema Field Naming:** The telephony duration field is stored as `duration_s` (in seconds) rather than `duration_seconds`.
3. **Investigation Stage Outliers:** While the median investigation latency is **44.5 seconds**, complex multi-clause statutory evaluations with extensive chunk contexts can peak at **288 seconds** under low Cloud Run concurrency.

---

## Strategic Product Roadmap

### Phase 3: Enterprise Hardening (Next Steps)

Planned near-term engineering enhancements:

- [ ] **Dual-Region Cloud SQL High Availability:** Upgrade Cloud SQL from single-zone `db-f1-micro` to a multi-zone regional instance with automated cross-region read replicas.
- [ ] **Active Directory / Okta SAML 2.0 Integration:** Implement enterprise SSO integration for institutional audit officers, replacing standalone JWT tokens.
- [ ] **WebRTC Live Telephony Streaming:** Transition from post-call GCS object finalize processing to live WebRTC/SIP audio stream surveillance with chunked 5-second sliding windows.
- [ ] **Automated Query Reformulation Expansion:** Broaden the Investigation Agent's autonomous query reformulation when encountering complex regulatory amendments.

### Phase 4: Unimplemented Tier-3 Vision Features

The following features represent architectural concepts that are **not currently implemented** in the repository:

- [ ] **Model Armor Prompt Screening (`ARGUS_MODEL_ARMOR_ENABLED=false`):** Integrating Google Cloud Model Armor to screen incoming prompts and transcripts before LLM ingestion.
- [ ] **Cloud Tasks Asynchronous Queue Dispatch (`ARGUS_CLOUD_TASKS_ENABLED=false`):** Offloading heavy multi-candidate investigations from FastAPI background worker threads to dedicated Google Cloud Tasks queues for strict rate-limit pacing.
- [ ] **Firebase Authentication Gateway (`ARGUS_FIREBASE_AUTH_ENABLED=false`):** Multi-tenant external authentication gateway for third-party auditing firms.
- [ ] **Automated Voice Biometric RM Verification:** Using acoustic speaker embeddings to verify that the RM speaking on the call matches the employee ID assigned to the customer account.

---

## Related Documents

- [Product Overview](./OVERVIEW.md)
- [System Architecture](./ARCHITECTURE.md)
- [Testing & Benchmark](./TESTING.md)
- [Security & Governance](./SECURITY.md)
