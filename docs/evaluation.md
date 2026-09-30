# Evaluation Plan and Example Metrics

## What the PoC evaluates

The Evaluation tab runs 12 deterministic, synthetic scenarios covering covered
procedures, plan limits, missing evidence, excluded procedures, inactive or
unknown plans, mismatched invoice/request fields, and a duplicate invoice.
Expected outcomes are authored explicitly in
`src/reimbursement_poc/evaluation.py`. Each scenario runs with isolated
orchestrator state, except that the duplicate-invoice case includes one earlier
synthetic submission as setup.

This is a **rules-workflow smoke test**, not an evaluation of an AI model or an
estimate of production performance. The examples are small, deliberately
constructed, and not statistically representative.

## Classification metrics

Treat `APPROVED` as the positive class for the binary approval metrics:

- **Approval precision** = correctly approved examples / all examples the PoC
  approved. This highlights potentially unsafe approvals in a labeled test set.
- **Eligible-approval recall** = correctly approved examples / all examples
  manually labeled as eligible for approval. This highlights eligible cases the
  workflow failed to approve directly.
- **Approval F1** = harmonic mean of approval precision and recall.
- **Exact decision agreement** = all four-way predicted routes that match their
  manual expected route / all test scenarios.
- **Confusion matrix** = counts of expected versus predicted outcomes for
  `APPROVED`, `REJECTED`, `NEEDS_INFORMATION`, and `HUMAN_REVIEW`.
- **False approvals** and **missed eligible approvals** are exposed as counts in
  addition to rates.

An undefined precision or recall denominator is reported as zero for display and
must be interpreted as "no positive examples in this fixture", not as measured
zero performance.

## Workflow and business metric examples

- **Straight-through approval rate:** route-to-approval volume / total submissions.
- **Human review rate:** referrals / total submissions, broken down by reason.
- **More-information rate:** submissions returned for missing fields / total.
- **Median and p95 end-to-end cycle time:** complete submission to final decision
  or payment.
- **Complete-at-first-submission rate** and document rework rate.
- **Analyst handling time**, backlog size, and oldest-case age.
- **Appeal and overturn rates**, especially for rejections and risk referrals.
- **Cost per processed claim**, service reliability, and user satisfaction.

These workflow proportions in the app come only from the synthetic test fixture;
they are examples of metrics to instrument, not business targets. Establish a
production baseline and agree targets with claims operations before a pilot.
Balance efficiency with incorrect approvals, inappropriate denials, delays,
appeal outcomes, and subgroup fairness. Never optimize approval rate alone.

## A credible pilot evaluation

1. Agree on a written labeling guide with claims, compliance, and policy owners.
2. Build an appropriately sampled, de-identified, authorized dataset; preserve
   rare edge cases and avoid training/evaluation leakage.
3. Have qualified reviewers label outcomes; adjudicate disagreements and report
   inter-rater agreement.
4. Keep a held-out test set and report per-class precision, recall, F1, confusion
   matrix, confidence intervals, and subgroup analysis where lawful and suitable.
5. Compare against the current manual process and measure cycle time, first-pass
   completeness, human workload, appeals/overturns, reliability, and cost.
6. Require human review for uncertainty and define rollback, audit, and incident
   procedures before any limited deployment.

The current PoC does not contain representative claims, fraud labels, protected
attributes, a calibrated model, OCR, or a payment integration. Its outputs must
not be used to make real member decisions.
