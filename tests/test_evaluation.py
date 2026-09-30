from reimbursement_poc.evaluation import (
    build_evaluation_examples,
    evaluate_synthetic_cases,
)


def test_labeled_examples_match_the_demonstrated_routing_policy() -> None:
    examples = build_evaluation_examples()
    report = evaluate_synthetic_cases()

    assert len(examples) == 12
    assert all(row["correct"] for row in report["rows"])
    assert report["metrics"]["exact_decision_agreement"] == 1.0
    assert report["metrics"]["eligible_approval_recall"] == 1.0
    assert report["metrics"]["approval_precision"] == 1.0
    assert report["metrics"]["eligible_approval_f1"] == 1.0
    assert report["metrics"]["false_approval_count"] == 0
    assert report["confusion_matrix"]["HUMAN_REVIEW"]["HUMAN_REVIEW"] == 5
