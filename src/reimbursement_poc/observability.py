"""Minimal local telemetry with bounded labels and no claim payloads."""

import json
import logging
from collections import Counter, defaultdict


def configure_logging() -> None:
    logger = logging.getLogger("reimbursement_poc")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)


class Observability:
    def __init__(self) -> None:
        self._events: Counter[tuple[str, str]] = Counter()
        self._durations_ms: dict[str, list[float]] = defaultdict(list)
        self._logger = logging.getLogger("reimbursement_poc")

    def record(
        self,
        stage: str,
        outcome: str,
        duration_ms: float = 0.0,
        *,
        case_id: str | None = None,
        trace_id: str | None = None,
    ) -> None:
        self._events[(stage, outcome)] += 1
        self._durations_ms[stage].append(round(duration_ms, 3))
        event = {
            "event": "poc_stage",
            "stage": stage,
            "outcome": outcome,
            "duration_ms": round(duration_ms, 3),
        }
        if case_id is not None:
            event["case_id"] = case_id
        if trace_id is not None:
            event["trace_id"] = trace_id
        self._logger.info(json.dumps(event, sort_keys=True))

    def snapshot(self) -> dict[str, object]:
        return {
            "event_counts": {
                f"{stage}:{outcome}": count
                for (stage, outcome), count in sorted(self._events.items())
            },
            "average_duration_ms": {
                stage: round(sum(values) / len(values), 3)
                for stage, values in sorted(self._durations_ms.items())
                if values
            },
        }
