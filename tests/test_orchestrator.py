import pytest

from reimbursement_poc.domain import CaseStatus, ClaimRequest
from reimbursement_poc.observability import Observability
from reimbursement_poc.orchestrator import CaseOrchestrator

POLICIES = {
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
}


def claim(
    case_id: str = "CASE-1",
    plan_id: str = "PPO-100",
    procedure: str = "MRI-KNEE",
    invoice_id: str = "INV-1",
    invoice_date: str = "2026-09-01",
    request_date: str = "2026-09-01",
    include_physician: bool = True,
) -> ClaimRequest:
    medical_request = {"procedure_code": procedure, "service_date": request_date}
    if include_physician:
        medical_request["physician_id"] = "DR-SYNTHETIC"
    return ClaimRequest(
        case_id=case_id,
        member_id="MEMBER-SYNTHETIC",
        plan_id=plan_id,
        documents={
            "invoice": {
                "invoice_id": invoice_id,
                "amount": 900,
                "provider": "SYNTHETIC CLINIC",
                "service_date": invoice_date,
                "procedure_code": procedure,
            },
            "medical_request": medical_request,
        },
    )


def test_approves_covered_procedure_up_to_plan_limit() -> None:
    result = CaseOrchestrator(POLICIES).submit(claim())

    assert result.status is CaseStatus.APPROVED
    assert result.approved_amount == 750


def test_requests_missing_information_before_deciding_coverage() -> None:
    orchestrator = CaseOrchestrator(POLICIES)
    result = orchestrator.submit(claim(include_physician=False))

    assert result.status is CaseStatus.NEEDS_INFORMATION
    assert result.missing_items == ("medical_request.physician_id",)
    assert "physician_id" in orchestrator.customer_update("CASE-1")


def test_rejects_procedure_not_covered_by_plan() -> None:
    result = CaseOrchestrator(POLICIES).submit(claim(plan_id="BASIC-200"))

    assert result.status is CaseStatus.REJECTED
    assert result.reasons == ("procedure_not_covered",)


def test_escalates_unknown_plan_to_human() -> None:
    result = CaseOrchestrator(POLICIES).submit(claim(plan_id="UNKNOWN"))

    assert result.status is CaseStatus.HUMAN_REVIEW
    assert result.reasons == ("unknown_plan",)


def test_escalates_mismatched_dates_without_calling_it_fraud() -> None:
    result = CaseOrchestrator(POLICIES).submit(claim(invoice_date="2026-09-02"))

    assert result.status is CaseStatus.HUMAN_REVIEW
    assert result.risk_flags == ("service_date_mismatch",)


def test_escalates_invoice_procedure_mismatch() -> None:
    request = claim()
    documents = {
        **request.documents,
        "invoice": {**request.documents["invoice"], "procedure_code": "OTHER"},
    }
    result = CaseOrchestrator(POLICIES).submit(
        ClaimRequest(
            case_id=request.case_id,
            member_id=request.member_id,
            plan_id=request.plan_id,
            documents=documents,
        )
    )

    assert result.status is CaseStatus.HUMAN_REVIEW
    assert result.risk_flags == ("procedure_code_mismatch",)


def test_detects_duplicate_invoice_across_cases_and_exposes_redacted_metrics() -> None:
    telemetry = Observability()
    orchestrator = CaseOrchestrator(POLICIES, telemetry)
    orchestrator.submit(claim(case_id="CASE-1"))
    result = orchestrator.submit(claim(case_id="CASE-2"))

    assert result.status is CaseStatus.HUMAN_REVIEW
    assert result.risk_flags == ("duplicate_invoice_id",)
    snapshot = telemetry.snapshot()
    assert snapshot["event_counts"]["case_decision:APPROVED"] == 1
    assert snapshot["event_counts"]["case_decision:HUMAN_REVIEW"] == 1


def test_rejects_reusing_case_id_and_unknown_support_case() -> None:
    orchestrator = CaseOrchestrator(POLICIES)
    orchestrator.submit(claim())

    with pytest.raises(ValueError, match="already been submitted"):
        orchestrator.submit(claim())
    with pytest.raises(KeyError, match="was not found"):
        orchestrator.customer_update("CASE-MISSING")
