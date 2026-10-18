# ARGUS Documentation Hub

The central navigation index and reading guide for the ARGUS compliance intelligence platform documentation.

[Root README](../README.md) | [Next: Product Overview](./OVERVIEW.md)

---

## Table of Contents

- [Start Here](#start-here)
- [Reading Paths by Audience](#reading-paths-by-audience)
  - [Hackathon Judges and Reviewers](#hackathon-judges-and-reviewers)
  - [Software Engineers and Contributors](#software-engineers-and-contributors)
  - [DevOps and Cloud Operators](#devops-and-cloud-operators)
  - [Security and Compliance Auditors](#security-and-compliance-auditors)
- [Complete Documentation Catalog](#complete-documentation-catalog)
- [Related Documents](#related-documents)

---

## Start Here

ARGUS is an autonomous, explainable compliance intelligence platform engineered for the Banking, Financial Services, and Insurance (BFSI) sector. It monitors Relationship Manager (RM) mutual-fund sales calls, evaluates utterances against statutory SEBI and AMFI regulations, and constructs an auditable, timestamped Evidence Chain for compliance teams.

If you are new to the repository, follow this sequential reading order:

1. [Product Overview](./OVERVIEW.md) — Understand the BFSI compliance challenge, system workflow, and the Evidence Chain concept.
2. [Architecture](./ARCHITECTURE.md) — Explore the event-driven Google Cloud infrastructure, pipeline flow, and core design decisions.
3. [Agents & Hard Guardrails](./AGENTS.md) — Inspect the multi-agent design, tool schemas, and forensic guardrails.
4. [Screenshot Gallery](./GLIMPSE.md) — Visual walkthrough of all interface screens in dark and light themes.

---

## Reading Paths by Audience

### Hackathon Judges and Reviewers

For an end-to-end evaluation of technical rigor, architectural soundness, and real experimental findings:

- [Product Overview](./OVERVIEW.md) — The regulatory problem, workflow, and Evidence Chain.
- [Architecture](./ARCHITECTURE.md) — Cloud architecture, idempotency, and failure isolation.
- [Agents](./AGENTS.md) — Investigation Agent with hard programmatic guardrails.
- [Screenshot Gallery](./GLIMPSE.md) — Complete visual gallery of dark and light theme UIs.
- [Testing & Benchmark](./TESTING.md) — Real 3-way live benchmark comparison and stage latencies.

### Software Engineers and Contributors

For developing, extending, or maintaining the application:

- [Development Guide](./DEVELOPMENT.md) — Local mock environment setup, offline execution, and coding conventions.
- [Tech Stack](./TECH_STACK.md) — Runtime dependencies, frameworks, libraries, and design rationale.
- [Data Model](./DATA_MODEL.md) — Cloud SQL schema, entity relationships, and regulation chunk registry.
- [API Reference](./API.md) — Complete specification of all REST endpoints, schemas, and error codes.
- [Frontend Architecture](./FRONTEND.md) — React 18, Tailwind CSS, theme tokens, and component breakdown.

### DevOps and Cloud Operators

For provisioning infrastructure, monitoring health, and operating deployments:

- [Configuration Reference](./CONFIGURATION.md) — Comprehensive reference of all environment variables.
- [Deployment Guide](./DEPLOYMENT.md) — GCP resource provisioning, IAM least-privilege roles, and Cloud Run setup.
- [Observability](./OBSERVABILITY.md) — Cloud Trace distributed tracing, structured logging, and health metrics.

### Security and Compliance Auditors

For evaluating data governance, statutory protection, and algorithmic safety:

- [Security & Governance](./SECURITY.md) — Google Cloud Sensitive Data Protection (DLP), prompt injection defenses, and IAM boundaries.
- [Data Model](./DATA_MODEL.md) — Regulation registry mapping, statutory chunking, and citation grounding.
- [Roadmap & Limitations](./ROADMAP.md) — Documented known limitations and planned architectural enhancements.

---

## Complete Documentation Catalog

For submission preparation, start with the [Competition Readiness Recommendations](./COMPETITION_READINESS.md) and [Submission Playbook](./SUBMISSION_PLAYBOOK.md). Recommendations remain pending until implemented and verified.

| Document | Primary Focus | Key Source References |
|---|---|---|
| [OVERVIEW.md](./OVERVIEW.md) | Business context, BFSI compliance problem, workflow, and Evidence Chain | [`../backend/db/repositories/cases_repo.py`](../backend/db/repositories/cases_repo.py) |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System context, data flow, pipeline sequence, and design decisions | [`../backend/ingestion/pipeline_runner.py`](../backend/ingestion/pipeline_runner.py) |
| [TECH_STACK.md](./TECH_STACK.md) | Technology choices, versions, responsibilities, and rationale | [`../backend/requirements.txt`](../backend/requirements.txt), [`../frontend/package.json`](../frontend/package.json) |
| [AGENTS.md](./AGENTS.md) | Ingestion, Retrieval, Detection, Investigation, and Chat agents | [`../backend/agents/`](../backend/agents/) |
| [DATA_MODEL.md](./DATA_MODEL.md) | MySQL schema (19 tables), ER diagram, and regulation chunk registry | [`../data/schemas/argus_mysql_ddl.sql`](../data/schemas/argus_mysql_ddl.sql) |
| [API.md](./API.md) | REST API endpoints, parameters, payloads, and error codes | [`../backend/api/routes/`](../backend/api/routes/) |
| [FRONTEND.md](./FRONTEND.md) | React UI router, pages, components, owl toggle, and state | [`../frontend/src/`](../frontend/src/) |
| [CONFIGURATION.md](./CONFIGURATION.md) | Complete environment variable specification and mock/live defaults | [`../.env.example`](../.env.example), [`../backend/core/config.py`](../backend/core/config.py) |
| [DEVELOPMENT.md](./DEVELOPMENT.md) | Local mock-mode development, tests, conventions, and troubleshooting | [`../scripts/`](../scripts/) |
| [DEPLOYMENT.md](./DEPLOYMENT.md) | Google Cloud provisioning, Cloud Run, Eventarc, IAM, and teardown | [`../infra/`](../infra/) |
| [OBSERVABILITY.md](./OBSERVABILITY.md) | Cloud Trace spans, structured logging, health probes, and metrics | [`../backend/observability/`](../backend/observability/) |
| [SECURITY.md](./SECURITY.md) | Sensitive Data Protection (DLP), prompt injection defenses, and IAM | [`../backend/adapters/pii_redactor.py`](../backend/adapters/pii_redactor.py) |
| [TESTING.md](./TESTING.md) | Offline test suite, live Phase 2 suite, and 3-way benchmark results | [`../tests/`](../tests/), [`../backend/benchmark/`](../backend/benchmark/) |
| [GLIMPSE.md](./GLIMPSE.md) | Visual gallery of all UI pages side-by-side in dark and light themes | [`./glimpse/`](./glimpse/) |
| [ROADMAP.md](./ROADMAP.md) | Known limitations, open issues from Phase 2, and future milestones | [`../backend/benchmark/benchmark_report.md`](../backend/benchmark/benchmark_report.md) |

---

## Related Documents

- [Product Overview](./OVERVIEW.md)
- [System Architecture](./ARCHITECTURE.md)
- [Testing & Benchmark](./TESTING.md)
