"""Sequential orchestration and case-status lookup for the local demo."""

from collections.abc import Callable
from time import perf_counter
from typing import TypeVar

from reimbursement_poc.agents import (
    CoverageAgent,
    DocumentReviewAgent,
    RiskSignalAgent,
)
from reimbursement_poc.domain import (
    CaseRecord,
    CaseStatus,
    ClaimRequest,
    CoverageFinding,
    CoverageStatus,
)
from reimbursement_poc.observability import Observability

Result = TypeVar("Result")


class CaseOrchestrator:
    def __init__(
        self,
        policies: dict[str, dict[str, object]],
        observability: Observability | None = None,
    ) -> None:
        self.documents = DocumentReviewAgent()
        self.coverage = CoverageAgent(policies)
        self.risk = RiskSignalAgent()
        self.observability = observability or Observability()
        self.cases: dict[str, CaseRecord] = {}

    def submit(self, request: ClaimRequest) -> CaseRecord:
        if request.case_id in self.cases:
            raise ValueError(f"Case {request.case_id} has already been submitted")

        started = perf_counter()
        missing_items = self._measure(
            "document_review", lambda: self.documents.review(request)
        )
        coverage = self._measure(
            "coverage_review", lambda: self.coverage.review(request)
        )
        risk_flags = self._measure(
            "risk_signal_review", lambda: self.risk.review(request)
        )
        status, reasons, approved_amount = self._decide(
            missing_items, coverage, risk_flags
        )
        record = CaseRecord(
            request=request,
            status=status,
            missing_items=missing_items,
            coverage=coverage,
            risk_flags=risk_flags,
            reasons=reasons,
            approved_amount=approved_amount,
        )
        self.cases[request.case_id] = record
        self.observability.record(
            "case_decision", status.value, (perf_counter() - started) * 1000
        )
        return record

    def customer_update(self, case_id: str) -> str:
        record = self.cases.get(case_id)
        if record is None:
            raise KeyError(f"Case {case_id} was not found")
        if record.status is CaseStatus.NEEDS_INFORMATION:
            return f"Please provide: {', '.join(record.missing_items)}."
        if record.status is CaseStatus.HUMAN_REVIEW:
            return "Your request is being reviewed by a specialist."
        if record.status is CaseStatus.REJECTED:
            return "Your request is not covered under the submitted plan."
        return "Your request has been approved under the submitted plan."

    def _measure(self, stage: str, operation: Callable[[], Result]) -> Result:
        started = perf_counter()
        result = operation()
        self.observability.record(stage, "completed", (perf_counter() - started) * 1000)
        return result

    @staticmethod
    def _decide(
        missing_items: tuple[str, ...],
        coverage: CoverageFinding,
        risk_flags: tuple[str, ...],
    ) -> tuple[CaseStatus, tuple[str, ...], float | None]:
        if missing_items:
            return (
                CaseStatus.NEEDS_INFORMATION,
                ("required_document_fields_missing",),
                None,
            )
        if coverage.status is CoverageStatus.NOT_COVERED:
            return CaseStatus.REJECTED, (coverage.reason,), None
        if coverage.status is CoverageStatus.UNKNOWN:
            return CaseStatus.HUMAN_REVIEW, (coverage.reason,), None
        if risk_flags:
            return CaseStatus.HUMAN_REVIEW, risk_flags, None
        return (
            CaseStatus.APPROVED,
            (coverage.reason,),
            coverage.eligible_amount,
        )
