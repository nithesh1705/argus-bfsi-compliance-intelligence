# ARGUS competition readiness recommendations

[Documentation hub](./INDEX.md) | [Submission playbook](./SUBMISSION_PLAYBOOK.md)

Reviewed on 18 October 2026 against commit `060615c1aaf16c0f4991d2b8070b624d1bc928b0`.
This is a proposed improvement plan based on source inspection and published artifacts. Runtime behavior, deployment access, and live benchmark results were not independently verified. Every checkbox below is pending; merging this document does not implement the recommendations.

## Quality target and judging alignment

Treat **9.9/10 as an internal ambition**, conditional on demonstrated results, rather than an achieved rating or prediction of placement. The [official criteria](https://aibuildercup.com/themes.html) weight technical implementation at 40%, impact at 25%, innovation at 25%, and user experience at 10%. The [official timeline](https://aibuildercup.com/#timeline) lists submission on 18 October 2026; verify the exact cutoff and timezone in the participant dashboard.

| Criterion | Strongest submission evidence | Current gap | Release gate |
|---|---|---|---|
| Technical, 40% | Reproducible evaluation and trustworthy evidence chain | Citation substitution, permissive quote alignment, mixed benchmark provenance | Regression tests for P0 findings and a versioned evaluation bundle |
| Impact, 25% | Measured improvement for a named compliance officer workflow | No practitioner study was identified in the reviewed benchmark | Small timed study with sample size, errors, and limitations |
| Innovation, 25% | Multilingual context linked to audio, product context, and supporting clauses | Published keyword baseline beats ARGUS on the small strict evaluation set | Honest comparison on held-out contextual cases; demonstrate evidence quality as well as classification |
| Experience, 10% | A judge can inspect and review a finding without assistance | Demo video section is a placeholder; current access needs verification | Fresh-browser walkthrough, working video, clear review states |

## P0: evidence integrity before stronger claims

### R1. Reject citation substitution

**Observed:** In [investigation_agent.py](../backend/agents/investigation_agent.py), `run_investigation_for_candidate` replaces an unknown model citation with `retrieved_passages[0].chunk_id`. At that point the earlier guard has already ensured passages exist, so the mismatch rejection in the empty-passages branch does not protect this path. The behavior conflicts with the exact-match guarantee in [agent documentation](./AGENTS.md).

- [ ] Remove automatic substitution. Preserve the original model output and record a citation-mismatch reason.
- [ ] Route the candidate to human review; create no confirmed finding from that decision.
- [ ] Add a mocked regression: model confirms citation `X`, retrieval contains only `A` and `B`; assert no finding commit, no substitution, and a persisted review/audit outcome.
- [ ] Add a positive control where a supported citation and verified quote can proceed.

**Acceptance:** An invented citation cannot become a confirmed case merely because another passage was retrieved. Citation membership is necessary but does not establish that a passage supports the allegation; separately inspect support and contradicting evidence.

### R2. Separate quote alignment from quote verification

**Observed:** [resolve_best_matching_quote](../backend/agents/detection_agent.py) permits timestamp-only matching and a fallback retaining model text. It searches exact and token matches across segments without restricting them to RM speech. The investigator consumes the returned text without an explicit match-validity result.

- [ ] Return segment ID, speaker, match method, and verification status explicitly.
- [ ] Require verified RM attribution for allegations about RM speech. Keep original-language evidence alongside translation.
- [ ] Validate `0 <= start_ms < end_ms <= duration_ms`; zero is a legitimate start timestamp. Use the verified segment interval consistently in the saved finding.
- [ ] Send unsupported quotes, ambiguous speaker mappings, and timestamp-only matches to review. A nearby timestamp must not certify the model's wording.
- [ ] Test fabricated text, empty segments, customer-only matches, reversed/out-of-range intervals, and valid RM speech beginning at zero.

**Acceptance:** No confirmed utterance finding lacks a verifiable source segment and speaker. Evaluate missing-disclosure allegations separately: absence needs sufficient call context, not an invented quote.

### R3. Keep insufficient evidence visible

**Observed:** Missing retrieval returns `DISMISSED_NO_CITATION` in [investigation_agent.py](../backend/agents/investigation_agent.py). `ESCALATE_FOR_REVIEW` exists in the output schema, but its persistence and visibility across workflow, API, and UI need end-to-end verification.

- [ ] Distinguish confirmed concern, reviewed dismissal, insufficient evidence, processing failure, and pending human review.
- [ ] Propagate review state through storage, API, counters, filters, and case details. Verify migrations and compatibility before changing outcome values.
- [ ] Never present unresolved evidence or processing failures as compliant calls.
- [ ] Test missing retrieval and ambiguous speaker attribution through the user-visible review queue, including audit history after adjudication.

**Acceptance:** Every unresolved candidate is discoverable by a reviewer; completion of processing is distinct from a compliance conclusion.

## P0: reproducible evaluation

### R4. Fix provenance before expanding performance claims

The [published report](../backend/benchmark/benchmark_report.md) has keyword F1 100%, detection F1 80%, and full-pipeline F1 92.3%. Ten demo calls are listed, but the ambiguous case is excluded from strict scoring: six positive and three clean calls remain. The investigation stage reduces false positives from three to one versus detection alone; that is **two corrected calls**, not evidence of broad market performance.

The [harness](../backend/benchmark/run_benchmark.py) reads baseline predictions from local candidate JSON and AI predictions from database state. Missing baseline files become clean predictions. Timing queries aggregate database history without evaluation-run filtering; the report timestamp is hardcoded and the Markdown positive denominator is fixed at six. These are reproducibility risks, not proof that the results are fabricated.

- [ ] Recompute the baseline from the same frozen inputs or attach immutable input and prediction manifests proving provenance. Treat missing artifacts or unprocessed calls as incomplete evaluation, never clean.
- [ ] Record run ID, actual UTC timestamp, commit, model IDs actually used, prompt version, corpus version, hashes, retry policy, and provider mode.
- [ ] Scope predictions, timing, and costs to that run; disclose retries and failures. Derive all denominators and exclusions from the manifest.
- [ ] Keep the ambiguous case separate under a predeclared rule; show review coverage and excluded counts alongside strict precision/recall/F1.
- [ ] Reconcile README, TESTING, JSON, and Markdown from one result bundle. Document actual models: the current benchmark reports `gemini-2.5-flash`, while some architecture text names other defaults.

**Acceptance:** A second person can trace every metric to a labelled input and prediction. A missing prediction causes an explicit incomplete result. No claim of outperforming keywords appears unless a fair evaluation demonstrates it.

### R5. Evaluate the cases that require context

Proposed next evaluation: 40 held-out synthetic or consented recordings, labelled before running the models. Separate development examples from evaluation by scenario family; paraphrases of one script must not span both sets. Use two independent annotators and adjudicate disagreements. Practitioner validation of regulatory labels remains necessary.

| Scenario family | Calls | Required distinction |
|---|---:|---|
| Explicit/indirect return promises | 8 | Direct wording versus implied assurance |
| Negation and reported speech | 8 | A promise versus denying or quoting a promise |
| Customer/RM attribution | 6 | Same phrase spoken by different people |
| Suitability and product context | 6 | Same pitch with different risk profiles |
| Multilingual/code-switching | 6 | Equivalent intent across languages |
| Noisy/overlapping/truncated speech | 6 | Supportable conclusion versus insufficient evidence |

Include clean and concerning cases across applicable families, not one label per family. Run keyword, detection-only, and full pipeline on identical inputs. Report confusion counts, per-category and per-language results with sample sizes, citation support, speaker attribution, review rate, and processing failure rate. Separate text-only reasoning evaluation from end-to-end audio evaluation. Report uncertainty; this remains a small study.

**Acceptance:** Publish all outcomes, including baseline wins and abstentions. Set decision thresholds before evaluation; do not tune against held-out labels to achieve a desired score.

## P1: differentiation, impact, and operational credibility

### R6. Prove the evidence chain in one workflow

- [ ] Demonstrate original audio, original/translated quote, verified speaker, customer/product context, and the exact supporting passage in one case.
- [ ] Display regulation document, page, clause, version, source, and applicability date. Review historical calls against applicable rules; filtering only on `current` is insufficient for historical validity.
- [ ] Correct the retrieval description: [the current live adapter](../backend/adapters/retriever.py) uses weighted token matching over Cloud SQL rows. Its class name does not demonstrate semantic retrieval or an external File Search invocation. Describe the implementation accurately; evaluate a semantic/hybrid alternative separately if added.
- [ ] Compare workflow and evidence quality against a rules-only approach and a generic transcript chatbot. Any competitor-specific comparison needs public sources or direct testing.

### R7. Measure reviewer benefit and cost

- [ ] Ask 2–3 compliance practitioners to review the same small case set manually and with ARGUS; counterbalance order to reduce learning effects.
- [ ] Record time, correct decisions, incorrect alerts, missed concerns, evidence usefulness, and assistance required. Distinguish measured values from estimates.
- [ ] Report median time saved as `(manual median - assisted median) / manual median`, together with raw observations and sample size; include slower or unsuccessful cases.
- [ ] Publish per-audio-minute variable cost from run-scoped usage, plus fixed database/hosting costs separately. Include retries and a clearly labelled monthly volume scenario.
- [ ] Measure p50/p95 latency and failure rate under stated concurrency. Until then, describe the product as post-call analysis; the current report averages 158.9 seconds and reaches 464.4 seconds.

### R8. Verify judge access and submission completeness

- [ ] Test the deployed application in a fresh browser with the exact reviewer access instructions supplied through the submission channel.
- [ ] Use isolated synthetic demo data and least-privilege access; do not expose institutional casework or publish production credentials.
- [ ] Add the public three-minute video and PDF deck links only after verifying access while signed out.
- [ ] Demonstrate loading, error, and review-needed states. Keep a clearly labelled processed case available if live processing is slow.
- [ ] Verify database-backed demo actions, audio seeking, citation navigation, and reviewer audit history end to end.

## Execution order

| Order | Work | Suggested role | Completion evidence |
|---|---|---|---|
| 1 | R1–R3 trust boundaries | Backend + frontend | Regression results and review-queue walkthrough |
| 2 | R4 evaluation provenance | Evaluation engineer | Reproducible manifest and reconciled report |
| 3 | R8 and submission playbook | Demo owner | Working links and timed signed-out rehearsal |
| 4 | R5 expanded evaluation | Evaluation + domain reviewer | Frozen labels, predictions, failures, limitations |
| 5 | R6–R7 differentiation and impact | Product + domain reviewer | Evidence comparison and timed study |

On deadline day, complete a smaller truthful submission if the full study cannot finish. Document remaining gaps. Defer streaming, biometric identification, SSO, and infrastructure expansion until the evidence workflow is dependable. Do not add untested features immediately before recording.

## Readiness decision

An internal near-perfect rating requires verified evidence integrity, reproducible evaluation, meaningful user benefit, and a reliable demonstration. Mark readiness as **pending** until the gates above have supporting artifacts. Placement depends on judges and competing submissions; this plan makes no prediction.
