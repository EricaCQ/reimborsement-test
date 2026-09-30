"""Small domain types shared by the demo agents."""

from dataclasses import dataclass
from enum import StrEnum


class CaseStatus(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    NEEDS_INFORMATION = "NEEDS_INFORMATION"
    HUMAN_REVIEW = "HUMAN_REVIEW"


class CoverageStatus(StrEnum):
    COVERED = "COVERED"
    NOT_COVERED = "NOT_COVERED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ClaimRequest:
    case_id: str
    member_id: str
    plan_id: str
    documents: dict[str, dict[str, object]]


@dataclass(frozen=True)
class CoverageFinding:
    status: CoverageStatus
    reason: str
    eligible_amount: float | None = None


@dataclass(frozen=True)
class TraceEntry:
    component: str
    latency_ms: float
    outcome_status: str


@dataclass(frozen=True)
class CaseRecord:
    request: ClaimRequest
    status: CaseStatus
    missing_items: tuple[str, ...]
    coverage: CoverageFinding
    risk_flags: tuple[str, ...]
    reasons: tuple[str, ...]
    approved_amount: float | None
    trace_id: str
    execution_trace: tuple[TraceEntry, ...]
    total_workflow_latency_ms: float
