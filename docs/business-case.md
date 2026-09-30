# Reimbursement business case — interview walkthrough

## One-minute summary

The proposal is a human-supervised reimbursement workflow, not an autonomous
fraud judge. A digital intake captures invoices and medical requests; specialist
agents check document completeness, plan/procedure coverage and explainable
inconsistency signals. A deterministic orchestrator routes straightforward,
policy-confirmed cases to approval, explicit exclusions to rejection, missing
documents back to the member, and uncertainty or risk signals to a human claims
analyst. A case-status channel reduces "where is my reimbursement?" contacts.

The supplied PoC demonstrates this decision flow on synthetic structured
examples. It does not parse real documents, connect to an insurer, or establish
production compliance, scale or service levels.

## Proposed workflow

1. **Intake:** secure web/mobile channel creates a case and collects the invoice
   and medical request; validate file type, size and malware before parsing.
2. **Document agent:** OCR/extraction in a production design populates a schema;
   the current PoC starts from pre-extracted synthetic fields and identifies gaps.
3. **Coverage agent:** retrieves the effective, versioned plan and policy rules;
   validates that the procedure and dates are eligible and calculates the
   reimbursable amount.
4. **Integrity agent:** checks duplicates and cross-document inconsistencies.
   Signals route to review; they do not establish fraud.
5. **Decision orchestrator:** transparent rules approve only complete cases with
   confirmed coverage; reject explicit exclusions; ask for missing evidence;
   escalate uncertainty, unusual signals and exceptions.
6. **Human review:** analyst sees evidence, policy version, reason codes and
   audit history; analyst can correct, override with a reason, or request data.
7. **Status/support:** authenticated members see a status and an understandable
   next step without exposing internal risk signals or another member's case.

## Why agents and where not to use them

The agents separate bounded responsibilities and can be evaluated independently.
Policy retrieval and eligibility remain deterministic and version-controlled.
An LLM may assist with extraction or plain-language drafting only behind
validation and human controls; it must not create policy, make an unreviewed
adverse decision, or label a member fraudulent. The demo's optional LLM adapter
rewrites generic reason codes only and is not invoked by default.

## Controls to discuss

- Minimize and protect health/financial data; encrypt, strictly authorize,
  segregate duties, apply retention limits and audit access/decisions.
- Use approved document/LLM providers and review their retention, region,
  contracts and training settings; default to no external LLM transmission.
- Version policy data and rules; test edge cases and monitor decision quality,
  outcome disparities, override rates and appeal outcomes.
- Keep a human appeal path; show clear reasons and collect only necessary
  information. Treat anomaly indicators as review signals, never proof.
- Design for idempotent submissions, durable state, retries, dead-letter review,
  backups, fail-closed policy uncertainty, disaster recovery and accessibility.

## Success measures and discovery questions

Establish a baseline before setting targets:

- Median and p95 time from complete submission to decision/payment.
- Percentage of complete-at-first-submission; missing-document rework rate.
- Straight-through processing rate **alongside** overturn, appeal and error rates.
- Human referrals by reason, analyst handling time and backlog age.
- Member contacts per claim and satisfaction.
- Reliability, p95 latency, cost per claim and access/audit exceptions.

Ask the business to confirm reimbursement rules, data sources, current volumes,
jurisdictions, fraud-review process, human staffing/capacity, service targets,
existing channels and permitted cloud/LLM providers before sizing production.

## Suggested interview walkthrough (about 5 minutes)

1. **Problem and goal (45 sec):** manual work, incomplete submissions and
   coverage checks create avoidable delay; propose faster, traceable triage.
2. **Architecture (60 sec):** open `presentations/architecture.excalidraw` and
   trace intake → bounded agents → policy router → human/customer outcomes.
3. **Live demo (2 min):** run the notebook's four synthetic cases: covered,
   missing evidence, excluded procedure and a repeated invoice/inconsistency.
   Show the decision, explanation, status response and aggregate timings.
4. **Safety (60 sec):** explain that deterministic policy is authoritative,
   anomaly signals are not fraud findings, ambiguous cases go to humans, and
   the sample contains no real customer data or external calls.
5. **Roadmap and measures (45 sec):** propose a governed pilot, baseline KPIs,
   security/privacy review, durable case state, document extraction, monitoring
   and explicit SLOs before production claims.

## Slide outline

The editable Excalidraw file is the architecture visual; use these headings for
slides:

1. **The opportunity:** shorter cycle time without sacrificing control.
2. **The proposed member journey:** submit, validate, decide, track.
3. **A supervised multi-agent workflow:** bounded agents and deterministic
   orchestration.
4. **Trust by design:** policy traceability, human review, privacy and audit.
5. **How we measure value:** baseline, balanced KPIs and pilot gates.
6. **PoC and next decisions:** what runs today, what is intentionally out of scope,
   and what the business must confirm.
