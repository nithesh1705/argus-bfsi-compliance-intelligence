# ARGUS submission playbook

[Documentation hub](./INDEX.md) | [Readiness recommendations](./COMPETITION_READINESS.md)

Proposed preparation material, 18 October 2026. Suggested copy describes the intended value proposition; verify each demonstrated capability before using it. This file is not a completed video, deck, practitioner study, or implementation.

## Positioning

**One sentence:** ARGUS helps compliance officers investigate multilingual sales calls through timestamped audio evidence, regulatory citations, and traceable human decisions.

**Opening:** A concerning sales statement is only the start of an investigation. A reviewer needs to know who said it, what product and customer context applied, which rule supports the concern, and what decision was made. ARGUS brings those pieces into one review workflow.

**Why Gen AI:** Evaluate contextual language, code-switching, indirect assurances, and supporting or contradicting evidence. Demonstrate a specific example where that context changes the result. Use the evidence chain as the product's defining feature; the number of agents is not itself proof of value.

## Three-minute demonstration

Use synthetic or consented material. Precheck the expected outcomes against the frozen evaluation. Never script a model success that has not been observed.

| Time | Screen/action | Narration goal |
|---|---|---|
| 0:00–0:20 | One named reviewer task | Explain user, problem, and decision to make |
| 0:20–0:45 | Open a processed multilingual call | Identify relevant speaker and original/translated phrase |
| 0:45–1:20 | Open finding and seek audio | Show the exact audible evidence and context |
| 1:20–1:45 | Open regulatory citation | Show source passage, page, and why it applies |
| 1:45–2:10 | Compare a negated/customer-spoken phrase | Explain correct dismissal or uncertainty using observed output |
| 2:10–2:35 | Reviewer decides and reopens audit history | Demonstrate human control and traceability |
| 2:35–3:00 | One architecture/evaluation slide | Explain Google Cloud roles, measured result, and one limitation |

Identify processed cases as processed cases. If showing a fresh upload, display actual progress and elapsed time; label any edit that skips waiting. The existing report's average processing time is approximately 159 seconds, so prepare the evidence case before the recording. If review-needed workflow is not yet implemented, describe it as planned rather than implying it exists.

## Six-slide PDF deck outline

1. **User and problem:** Compliance reviewer, sales-call workflow, and consequences of missed or unsupported allegations. Cite any industry figures; remove unsupported prevalence claims.
2. **Product:** Audio → transcript/speaker → context → clause → reviewer decision. Use one readable real application screenshot.
3. **Why this approach:** Contextual example, evidence provenance, uncertainty handling, and human adjudication. Distinguish implemented behavior from proposals.
4. **Architecture:** Show actual Cloud Run, Vertex AI, Cloud Storage, Eventarc, Cloud SQL, and DLP responsibilities. Identify the deployed model and implemented retrieval method accurately.
5. **Evidence:** Run ID/date, evaluated count and exclusions, baseline comparison, reviewer observations, latency, and cost. Keep preliminary results labelled preliminary.
6. **Adoption:** First target user, integration path, measured pilot outcome if available, limitations, and next validation milestone. Any scale or savings scenario must state its assumptions.

## Claim review before publishing

| Claim to review | Recommended treatment |
|---|---|
| “100% automated surveillance” | State which uploaded calls are processed and how failures/review cases are counted; do not imply perfect detection |
| “Zero hallucinations” or absolute attribution guarantees | Describe tested checks and residual failure modes; fix citation/quote issues first |
| “67% fewer false positives” | Say two of three detection-only false positives were removed in the nine-call strict evaluation |
| “Outperforms keywords” | Current published classification results do not establish this; report the baseline honestly |
| “Real-time” | Use post-call analysis and report measured latency until streaming is implemented and measured |
| “Semantic/File Search retrieval” | Describe current weighted token matching over Cloud SQL unless a different implementation is demonstrated |
| Industry audit coverage, adoption, or savings figures | Add a supporting source or measured study; otherwise remove or label an assumption |
| Enterprise readiness | Distinguish prototype controls from SSO, load testing, HA, and other unimplemented roadmap items |

## Rehearsal and submission checklist

- [ ] Official submission dashboard checked for the exact deadline/timezone and required fields.
- [ ] BFSI theme selected; use the dashboard's actual category options. The public requirements page also contains a conflicting generic category list; resolve against the dashboard or organizer guidance rather than guessing.
- [ ] Public three-minute video tested while signed out; captions and interface text are legible.
- [ ] PDF deck opens correctly and uses the same metrics as the versioned report.
- [ ] Live prototype, repository, and reviewer access instructions are available through the submission.
- [ ] Reviewer path rehearsed from a fresh browser with synthetic data: open case, seek audio, open citation, record review, inspect history.
- [ ] Failures or incomplete analyses are visible; prepared cases are labelled accurately.
- [ ] Actual models/provider mode and implemented services agree with the architecture slide.
- [ ] README demo-video placeholder replaced with a verified link by the team.
- [ ] Submission saved and its confirmation recorded by the team before cutoff.

## Likely judge questions

**Why did keywords win your benchmark?** The existing demo set is small and favorable to explicit patterns. Present that result directly, then show held-out contextual evaluation if completed. Evidence quality and reviewer usefulness must be measured separately from classification.

**What happens when the model cannot verify a concern?** Demonstrate the actual review state and audit behavior. If the proposed state propagation is unfinished, disclose the limitation.

**How do you know the citation supports the finding?** Show the exact passage and applicability, with supporting and contradicting evidence. A valid chunk ID alone proves neither relevance nor legal correctness.

**Will this work at institutional scale?** State the concurrency and volume actually tested, fixed and variable costs, and failure/retry behavior. Present larger volumes as projections until measured.

## Sources

- [Official requirements and judging criteria](https://aibuildercup.com/themes.html), checked 18 October 2026.
- [Official timeline](https://aibuildercup.com/#timeline), checked 18 October 2026.
- [Published benchmark](../backend/benchmark/benchmark_report.md) and [testing limitations](./TESTING.md).
- [Known limitations and future work](./ROADMAP.md).
