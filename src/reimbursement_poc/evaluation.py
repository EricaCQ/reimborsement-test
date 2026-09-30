"""Synthetic, labeled examples and evaluation metrics for the rules-based PoC."""

from dataclasses import dataclass
from typing import TypedDict

from reimbursement_poc.domain import CaseStatus, ClaimRequest
from reimbursement_poc.orchestrator import CaseOrchestrator

SYNTHETIC_POLICIES: dict[str, dict[str, object]] = {
    "PPO-100": {
        "active": True,
        "covered_procedures": ["MRI-KNEE", "CARDIO-CONSULT"],
        "max_reimbursement": 750,
    },
    "BASIC-200": {
        "active": True,
        "covered_procedures": ["CARDIO-CONSULT"],
        "max_reimbursement": 250,
    },
    "PLAN-WITHOUT-RULE": {"active": True, "max_reimbursement": 500},
    "INACTIVE-300": {
        "active": False,
        "covered_procedures": ["MRI-KNEE"],
        "max_reimbursement": 500,
    },
}

STATUSES = tuple(status.value for status in CaseStatus)


@dataclass(frozen=True)
class EvaluationExample:
    scenario: str
    request: ClaimRequest
    expected_status: CaseStatus
    prior_requests: tuple[ClaimRequest, ...] = ()


class EvaluationRow(TypedDict):
    scenario: str
    expected: str
    predicted: str
    correct: bool
    reason_codes: str
    approved_amount: float | None


def _request(
    case_id: str,
    *,
    plan_id: str = "PPO-100",
    procedure: str = "MRI-KNEE",
    invoice_procedure: str | None = None,
    amount: float = 400,
    invoice_date: str = "2026-09-01",
    request_date: str = "2026-09-01",
    invoice_id: str | None = None,
    include_invoice: bool = True,
    include_physician: bool = True,
) -> ClaimRequest:
    medical_request: dict[str, object] = {
        "procedure_code": procedure,
        "service_date": request_date,
    }
    if include_physician:
        medical_request["physician_id"] = "DR-SYNTHETIC"
    documents: dict[str, dict[str, object]] = {
        "medical_request": medical_request,
    }
    if include_invoice:
        documents["invoice"] = {
            "invoice_id": invoice_id or f"INV-{case_id}",
            "amount": amount,
            "provider": "SYNTHETIC CLINIC",
            "service_date": invoice_date,
            "procedure_code": invoice_procedure or procedure,
        }
    return ClaimRequest(
        case_id=case_id,
        member_id=f"MEMBER-{case_id}",
        plan_id=plan_id,
        documents=documents,
    )


def build_evaluation_examples() -> tuple[EvaluationExample, ...]:
    """Return deterministic scenarios with manually authored expected outcomes."""
    return (
        EvaluationExample(
            "Covered procedure; amount below plan limit",
            _request("EVAL-01", amount=400),
            CaseStatus.APPROVED,
        ),
        EvaluationExample(
            "Covered procedure; reimbursement capped at plan limit",
            _request("EVAL-02", amount=900),
            CaseStatus.APPROVED,
        ),
        EvaluationExample(
            "Second covered procedure",
            _request("EVAL-03", procedure="CARDIO-CONSULT"),
            CaseStatus.APPROVED,
        ),
        EvaluationExample(
            "Required physician field missing",
            _request("EVAL-04", include_physician=False),
            CaseStatus.NEEDS_INFORMATION,
        ),
        EvaluationExample(
            "Invoice not submitted",
            _request("EVAL-05", include_invoice=False),
            CaseStatus.NEEDS_INFORMATION,
        ),
        EvaluationExample(
            "Procedure excluded by plan",
            _request("EVAL-06", plan_id="BASIC-200"),
            CaseStatus.REJECTED,
        ),
        EvaluationExample(
            "Inactive plan",
            _request("EVAL-07", plan_id="INACTIVE-300"),
            CaseStatus.REJECTED,
        ),
        EvaluationExample(
            "Unknown plan requires policy verification",
            _request("EVAL-08", plan_id="UNKNOWN-999"),
            CaseStatus.HUMAN_REVIEW,
        ),
        EvaluationExample(
            "Service date mismatch requires review",
            _request("EVAL-09", invoice_date="2026-09-02"),
            CaseStatus.HUMAN_REVIEW,
        ),
        EvaluationExample(
            "Procedure mismatch requires review",
            _request("EVAL-10", invoice_procedure="OTHER-PROCEDURE"),
            CaseStatus.HUMAN_REVIEW,
        ),
        EvaluationExample(
            "Unknown covered-procedure list requires review",
            _request("EVAL-11", plan_id="PLAN-WITHOUT-RULE"),
            CaseStatus.HUMAN_REVIEW,
        ),
        EvaluationExample(
            "Duplicate invoice requires review",
            _request("EVAL-12", invoice_id="INV-EVAL-01"),
            CaseStatus.HUMAN_REVIEW,
            prior_requests=(_request("EVAL-SEED-12", invoice_id="INV-EVAL-01"),),
        ),
    )


def _ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def evaluate_synthetic_cases() -> dict[str, object]:
    """Evaluate exact routing and binary eligible-approval recall/precision."""
    rows: list[EvaluationRow] = []
    matrix = {
        expected: {predicted: 0 for predicted in STATUSES} for expected in STATUSES
    }

    for example in build_evaluation_examples():
        # Isolate each scenario so state from another example cannot affect it.
        orchestrator = CaseOrchestrator(SYNTHETIC_POLICIES)
        for prior_request in example.prior_requests:
            orchestrator.submit(prior_request)
        record = orchestrator.submit(example.request)
        expected = example.expected_status.value
        predicted = record.status.value
        matrix[expected][predicted] += 1
        rows.append(
            {
                "scenario": example.scenario,
                "expected": expected,
                "predicted": predicted,
                "correct": expected == predicted,
                "reason_codes": ", ".join(record.reasons),
                "approved_amount": record.approved_amount,
            }
        )

    total = len(rows)
    exact_matches = sum(row["correct"] for row in rows)
    actual_approvals = sum(row["predicted"] == CaseStatus.APPROVED for row in rows)
    expected_approvals = sum(row["expected"] == CaseStatus.APPROVED for row in rows)
    true_approvals = matrix[CaseStatus.APPROVED.value][CaseStatus.APPROVED.value]
    false_approvals = actual_approvals - true_approvals
    missed_approvals = expected_approvals - true_approvals
    approval_precision = _ratio(true_approvals, actual_approvals)
    approval_recall = _ratio(true_approvals, expected_approvals)

    metrics: dict[str, float | int] = {
        "evaluation_cases": total,
        "exact_decision_agreement": _ratio(exact_matches, total),
        "approval_precision": approval_precision,
        "eligible_approval_recall": approval_recall,
        "eligible_approval_f1": _ratio(
            2 * approval_precision * approval_recall,
            approval_precision + approval_recall,
        ),
        "straight_through_approval_rate": _ratio(actual_approvals, total),
        "human_review_rate": _ratio(
            sum(row["predicted"] == CaseStatus.HUMAN_REVIEW for row in rows), total
        ),
        "needs_information_rate": _ratio(
            sum(row["predicted"] == CaseStatus.NEEDS_INFORMATION for row in rows),
            total,
        ),
        "rejection_rate": _ratio(
            sum(row["predicted"] == CaseStatus.REJECTED for row in rows), total
        ),
        "false_approval_count": false_approvals,
        "missed_eligible_approval_count": missed_approvals,
    }
    return {"rows": rows, "metrics": metrics, "confusion_matrix": matrix}
