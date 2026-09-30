# Architecture, Controls, and PoC Limitations

## Workflow

1. The Streamlit app or notebook accepts a synthetic structured claim. This
   version does not upload files, run OCR, or extract fields from PDFs.
2. `DocumentReviewAgent` checks the minimum invoice and medical-request fields.
3. `CoverageAgent` checks a local synthetic plan/procedure catalogue and
   calculates an eligible amount up to the plan limit.
4. `RiskSignalAgent` checks simple inconsistencies, such as duplicate invoice
   identifiers and mismatched dates or procedure codes.
5. `CaseOrchestrator` applies deterministic rules and selects approval, rejection,
   a request for information, or human review.
6. Case state is held in memory; `customer_update` simulates a status response.
7. `Observability` records stages, outcomes, durations, and aggregate counts.

Implementation modules are in `src/reimbursement_poc/`; the notebook and
Streamlit app expose their behavior without hiding the source.

## Demonstrated decision policy

| Condition | Outcome |
| --- | --- |
| Required fields are missing | NEEDS_INFORMATION |
| Plan or procedure is explicitly not covered | REJECTED |
| Plan or rule is unknown or incomplete | HUMAN_REVIEW |
| Any inconsistency signal is present | HUMAN_REVIEW |
| Coverage is confirmed and no signal is present | APPROVED, up to the plan limit |

This precedence is illustrative and must be approved by claims, legal, compliance,
and product stakeholders before operational use. A signal is not proof of fraud;
the PoC does not make probabilistic adverse decisions.

## Security, privacy, and governance

- Use synthetic data only. Do not enter personal, health, or financial information
  in the demo or send it to AI providers.
- Before connecting real channels or sources, implement strong authentication,
  role-based authorization, separation of duties, encryption in transit/at rest,
  key management, and an audit trail.
- Define lawful basis, data minimization, retention, data subject rights, data
  residency, and a privacy impact assessment with the privacy/compliance teams.
  This PoC is not evidence of regulatory compliance.
- Version policies and rules, record approvals, test regressions, monitor outcome
  disparities, and provide explanations, appeals, and human review.
- The optional LLM sends only a status and generic reason codes to an
  OpenAI-compatible endpoint. It is disabled unless explicitly invoked; verify
  endpoint, retention, contract, and authorization before configuring credentials.
- `.env` is local and ignored by Git. Do not transfer personal credentials to a
  work device.

## Scalability, availability, and reliability gaps

Case state is currently an in-memory dictionary; logs and metrics are local.
Production would need APIs/channels, authentication/authorization, durable
transactional storage, an idempotent queue with retries and a dead-letter queue,
versioned policies, high availability, backups, disaster recovery, concurrency
limits, and load testing. Measure p50/p95/p99 latency by stage and define SLOs
before claiming low latency or availability.

## Demonstrated observability

Local JSON events contain only stage, outcome, and duration. `snapshot()` exposes
counts with bounded-cardinality labels and average durations in milliseconds.
Member/case IDs, documents, prompts, and tokens are not logged or used as metric
labels. A real deployment would add distributed tracing, centralized metrics,
alerts, protected correlation, and dashboards after privacy review.
