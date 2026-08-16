from __future__ import annotations

from collections import Counter
from typing import cast

from evaluations.runners.memory_quality import load_dataset, run_evaluation


def test_phase9_dataset_contains_30_balanced_synthetic_timelines() -> None:
    dataset = load_dataset()
    scenarios = Counter(item.scenario for item in dataset.timelines)

    assert dataset.synthetic_only is True
    assert len(dataset.timelines) == 30
    assert len(scenarios) == 15
    assert set(scenarios.values()) == {2}


def test_hybrid_trusted_retrieval_passes_every_release_gate() -> None:
    report = run_evaluation()
    approaches = cast(dict[str, dict[str, float | int]], report["approaches"])
    metrics = cast(dict[str, float | int], report["release_metrics"])
    gates = cast(dict[str, bool], report["release_gates"])

    assert isinstance(approaches, dict)
    assert isinstance(metrics, dict)
    assert report["passed"] is True
    assert all(gates.values())
    assert metrics["cross_subject_leakage_cases"] == 0
    assert metrics["correct_subject_scoped_retrieval_percent"] == 100
    assert metrics["memory_trace_reproducibility_percent"] == 100
    assert (
        approaches["hybrid_trusted_memory"]["expected_key_recall_percent"]
        > approaches["most_recent_report_only"]["expected_key_recall_percent"]
    )
    assert (
        approaches["hybrid_trusted_memory"]["safe_action_accuracy_percent"]
        > approaches["vector_similarity_only"]["safe_action_accuracy_percent"]
    )


def test_phase9_report_is_reproducible() -> None:
    assert run_evaluation() == run_evaluation()
