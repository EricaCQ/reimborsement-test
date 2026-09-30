"""Deterministic specialist agents for the synthetic demonstration."""

from reimbursement_poc.domain import (
    ClaimRequest,
    CoverageFinding,
    CoverageStatus,
)


class DocumentReviewAgent:
    required_fields = {
        "invoice": (
            "invoice_id",
            "amount",
            "provider",
            "service_date",
            "procedure_code",
        ),
        "medical_request": ("procedure_code", "physician_id", "service_date"),
    }

    def review(self, request: ClaimRequest) -> tuple[str, ...]:
        missing: list[str] = []
        for document_name, required_fields in self.required_fields.items():
            document = request.documents.get(document_name, {})
            for field_name in required_fields:
                if document.get(field_name) in (None, ""):
                    missing.append(f"{document_name}.{field_name}")
        return tuple(missing)


class CoverageAgent:
    def __init__(self, policies: dict[str, dict[str, object]]) -> None:
        self.policies = policies

    def review(self, request: ClaimRequest) -> CoverageFinding:
        policy = self.policies.get(request.plan_id)
        if policy is None:
            return CoverageFinding(CoverageStatus.UNKNOWN, "unknown_plan")
        if policy.get("active") is not True:
            return CoverageFinding(CoverageStatus.NOT_COVERED, "inactive_plan")

        invoice = request.documents.get("invoice", {})
        medical_request = request.documents.get("medical_request", {})
        procedure_code = medical_request.get("procedure_code")
        covered_procedures = policy.get("covered_procedures")
        if not isinstance(covered_procedures, list) or not isinstance(
            procedure_code, str
        ):
            return CoverageFinding(CoverageStatus.UNKNOWN, "coverage_data_incomplete")
        if procedure_code not in covered_procedures:
            return CoverageFinding(CoverageStatus.NOT_COVERED, "procedure_not_covered")

        amount = invoice.get("amount")
        maximum = policy.get("max_reimbursement")
        if (
            not isinstance(amount, (int, float))
            or isinstance(amount, bool)
            or not isinstance(maximum, (int, float))
            or isinstance(maximum, bool)
        ):
            return CoverageFinding(
                CoverageStatus.UNKNOWN, "amount_or_limit_unavailable"
            )
        return CoverageFinding(
            CoverageStatus.COVERED,
            "procedure_covered",
            eligible_amount=min(float(amount), float(maximum)),
        )


class RiskSignalAgent:
    """Flags inconsistencies for review; it does not label claims as fraud."""

    def __init__(self) -> None:
        self.seen_invoice_ids: set[str] = set()

    def review(self, request: ClaimRequest) -> tuple[str, ...]:
        invoice = request.documents.get("invoice", {})
        medical_request = request.documents.get("medical_request", {})
        flags: list[str] = []

        invoice_id = invoice.get("invoice_id")
        if isinstance(invoice_id, str):
            if invoice_id in self.seen_invoice_ids:
                flags.append("duplicate_invoice_id")
            else:
                self.seen_invoice_ids.add(invoice_id)

        if (
            invoice.get("service_date")
            and medical_request.get("service_date")
            and invoice["service_date"] != medical_request["service_date"]
        ):
            flags.append("service_date_mismatch")

        if (
            invoice.get("procedure_code")
            and medical_request.get("procedure_code")
            and invoice["procedure_code"] != medical_request["procedure_code"]
        ):
            flags.append("procedure_code_mismatch")
        return tuple(flags)
