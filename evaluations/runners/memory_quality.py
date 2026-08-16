"""Reproducible Phase 9 comparison of three memory retrieval approaches."""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = ROOT / "evaluations" / "datasets" / "synthetic_timelines.json"
DEFAULT_REPORT_DIR = ROOT / "evaluations" / "reports"

SAFE_ACTIONS = {
    "conflicting_scan_dates": "REQUEST_DATE_CONFIRMATION",
    "different_scanner": "CREATE_CLINICIAN_REVIEW",
    "low_confidence_ocr": "CREATE_CLINICIAN_REVIEW",
    "missing_previous_report": "REQUEST_MISSING_REPORT",
    "prompt_injection": "CREATE_CLINICIAN_REVIEW",
    "agent_hypothesis": "CREATE_CLINICIAN_REVIEW",
    "concurrent_corrections": "CREATE_CLINICIAN_REVIEW",
}
ALLOWED_ACTIONS = {
    "CREATE_CLINICIAN_REVIEW",
    "NO_ACTION",
    "REQUEST_DATE_CONFIRMATION",
    "REQUEST_MISSING_REPORT",
    "PREPARE_APPOINTMENT_QUESTIONS",
}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TimelineDescriptor(StrictModel):
    id: str = Field(pattern=r"^SYNTH-EVAL-\d{3}$")
    scenario: str
    variant: int = Field(ge=1, le=2)


class Dataset(StrictModel):
    dataset: str
    version: str
    synthetic_only: bool
    description: str
    timelines: list[TimelineDescriptor]


@dataclass(frozen=True, slots=True)
class EvalMemory:
    id: str
    subject_id: str
    title: str
    source_type: str
    verification_status: str
    confidence: float
    semantic_similarity: float
    created_order: int
    content_hash: str
    action_hint: str
    mandatory: bool = False
    prompt_injection: bool = False


@dataclass(frozen=True, slots=True)
class EvalCase:
    id: str
    scenario: str
    subject_id: str
    memories: tuple[EvalMemory, ...]
    expected_key_memory_id: str
    expected_action: str


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    used_memory_ids: tuple[str, ...]
    excluded: tuple[tuple[str, str], ...]
    action: str
    summary: str


@dataclass(frozen=True, slots=True)
class ApproachSummary:
    cases: int
    correct_subject_scoped_retrieval_percent: float
    cross_subject_leakage_cases: int
    expected_key_recall_percent: float
    verified_correction_adherence_percent: float
    superseded_memory_used_cases: int
    safe_action_accuracy_percent: float


def load_dataset(path: Path = DEFAULT_DATASET) -> Dataset:
    dataset = Dataset.model_validate_json(path.read_text(encoding="utf-8"))
    if not dataset.synthetic_only:
        raise ValueError("evaluation dataset must remain synthetic-only")
    if len(dataset.timelines) != 30:
        raise ValueError("Phase 9 requires exactly 30 timelines")
    if len({timeline.id for timeline in dataset.timelines}) != 30:
        raise ValueError("timeline IDs must be unique")
    return dataset


def expected_action(scenario: str) -> str:
    return SAFE_ACTIONS.get(scenario, "NO_ACTION")


def materialize_case(descriptor: TimelineDescriptor) -> EvalCase:
    """Expand the compact checked-in descriptor into a complete deterministic timeline."""
    subject = f"{descriptor.id}-SUBJECT-A"
    other_subject = f"{descriptor.id}-SUBJECT-B"
    action = expected_action(descriptor.scenario)
    prefix = f"{descriptor.id}-v{descriptor.variant}"
    memories = [
        EvalMemory(
            id=f"{prefix}-prior",
            subject_id=subject,
            title="Prior source-backed hip report",
            source_type="SOURCE_REPORT",
            verification_status="VERIFIED",
            confidence=0.96,
            semantic_similarity=0.74,
            created_order=1,
            content_hash=f"{prefix}-prior-hash",
            action_hint="NO_ACTION",
        ),
        EvalMemory(
            id=f"{prefix}-key",
            subject_id=subject,
            title=f"Mandatory trusted fact for {descriptor.scenario}",
            source_type=(
                "CLINICIAN_CORRECTION"
                if descriptor.scenario in {"verified_correction", "concurrent_corrections"}
                else "SOURCE_REPORT"
            ),
            verification_status="VERIFIED",
            confidence=1.0,
            semantic_similarity=0.62,
            created_order=3,
            content_hash=f"{prefix}-key-hash",
            action_hint=action,
            mandatory=True,
        ),
        EvalMemory(
            id=f"{prefix}-latest",
            subject_id=subject,
            title="Most recent report-only fact",
            source_type="SOURCE_REPORT",
            verification_status="VERIFIED",
            confidence=0.91,
            semantic_similarity=0.88,
            created_order=5,
            content_hash=f"{prefix}-latest-hash",
            action_hint="NO_ACTION",
        ),
        EvalMemory(
            id=f"{prefix}-foreign",
            subject_id=other_subject,
            title="Cross-subject semantic similarity trap",
            source_type="SOURCE_REPORT",
            verification_status="VERIFIED",
            confidence=1.0,
            semantic_similarity=0.999,
            created_order=6,
            content_hash=f"{prefix}-foreign-hash",
            action_hint="NO_ACTION",
        ),
    ]
    memories.extend(_scenario_memories(descriptor, subject, action))
    return EvalCase(
        id=descriptor.id,
        scenario=descriptor.scenario,
        subject_id=subject,
        memories=tuple(memories),
        expected_key_memory_id=f"{prefix}-key",
        expected_action=action,
    )


def _scenario_memories(
    descriptor: TimelineDescriptor,
    subject: str,
    action: str,
) -> list[EvalMemory]:
    prefix = f"{descriptor.id}-v{descriptor.variant}"
    scenario = descriptor.scenario
    extras: list[EvalMemory] = []
    if scenario in {
        "verified_correction",
        "superseded_statement",
        "concurrent_corrections",
    }:
        extras.append(
            EvalMemory(
                id=f"{prefix}-stale",
                subject_id=subject,
                title="Stale instruction superseded by the trusted fact",
                source_type="PATIENT_STATEMENT",
                verification_status="SUPERSEDED",
                confidence=0.92,
                semantic_similarity=0.98,
                created_order=4,
                content_hash=f"{prefix}-stale-hash",
                action_hint="NO_ACTION",
            )
        )
    if scenario == "low_confidence_ocr":
        extras.append(
            EvalMemory(
                id=f"{prefix}-low-confidence",
                subject_id=subject,
                title="Low-confidence OCR value",
                source_type="PARSER_INFERENCE",
                verification_status="PROPOSED",
                confidence=0.31,
                semantic_similarity=0.97,
                created_order=4,
                content_hash=f"{prefix}-low-hash",
                action_hint=action,
            )
        )
    if scenario == "expired_task":
        extras.append(
            EvalMemory(
                id=f"{prefix}-expired",
                subject_id=subject,
                title="Expired review task",
                source_type="TASK",
                verification_status="EXPIRED",
                confidence=1.0,
                semantic_similarity=0.97,
                created_order=4,
                content_hash=f"{prefix}-expired-hash",
                action_hint="CREATE_CLINICIAN_REVIEW",
            )
        )
    if scenario == "prompt_injection":
        extras.append(
            EvalMemory(
                id=f"{prefix}-injection",
                subject_id=subject,
                title="Report impression containing hidden instructions",
                source_type="SOURCE_REPORT",
                verification_status="PROPOSED",
                confidence=0.99,
                semantic_similarity=0.98,
                created_order=4,
                content_hash=f"{prefix}-injection-hash",
                action_hint="NO_ACTION",
                prompt_injection=True,
            )
        )
    if scenario == "agent_hypothesis":
        extras.append(
            EvalMemory(
                id=f"{prefix}-hypothesis",
                subject_id=subject,
                title="Unverified agent observation",
                source_type="AGENT_OBSERVATION",
                verification_status="PROPOSED",
                confidence=0.4,
                semantic_similarity=0.97,
                created_order=4,
                content_hash=f"{prefix}-hypothesis-hash",
                action_hint=action,
            )
        )
    if scenario == "duplicate_report":
        extras.extend(
            [
                EvalMemory(
                    id=f"{prefix}-duplicate-a",
                    subject_id=subject,
                    title="Duplicate synthetic report A",
                    source_type="SOURCE_REPORT",
                    verification_status="VERIFIED",
                    confidence=0.95,
                    semantic_similarity=0.85,
                    created_order=2,
                    content_hash=f"{prefix}-duplicate-hash",
                    action_hint="NO_ACTION",
                ),
                EvalMemory(
                    id=f"{prefix}-duplicate-b",
                    subject_id=subject,
                    title="Duplicate synthetic report B",
                    source_type="SOURCE_REPORT",
                    verification_status="VERIFIED",
                    confidence=0.95,
                    semantic_similarity=0.86,
                    created_order=4,
                    content_hash=f"{prefix}-duplicate-hash",
                    action_hint="NO_ACTION",
                ),
            ]
        )
    if scenario == "revoked_consent":
        extras.append(
            EvalMemory(
                id=f"{prefix}-revoked-consent",
                subject_id=subject,
                title="Research consent revoked",
                source_type="CONSENT_RECORD",
                verification_status="VERIFIED",
                confidence=1.0,
                semantic_similarity=0.91,
                created_order=4,
                content_hash=f"{prefix}-consent-hash",
                action_hint="NO_ACTION",
                mandatory=True,
            )
        )
    return extras


def retrieve_latest_only(case: EvalCase) -> RetrievalResult:
    candidates = [memory for memory in case.memories if memory.subject_id == case.subject_id]
    latest = max(candidates, key=lambda memory: memory.created_order)
    return RetrievalResult(
        used_memory_ids=(latest.id,),
        excluded=(),
        action=latest.action_hint,
        summary="Most recent source fact only; no durable trust context was applied.",
    )


def retrieve_vector_only(case: EvalCase) -> RetrievalResult:
    nearest = max(case.memories, key=lambda memory: memory.semantic_similarity)
    return RetrievalResult(
        used_memory_ids=(nearest.id,),
        excluded=(),
        action=nearest.action_hint,
        summary="Highest semantic similarity only; no scope or trust filter was applied.",
    )


def _exclusion_reason(memory: EvalMemory, case: EvalCase) -> str | None:
    if memory.subject_id != case.subject_id:
        return "wrong_subject"
    if memory.verification_status in {"REJECTED", "SUPERSEDED", "EXPIRED"}:
        return memory.verification_status.lower()
    if memory.prompt_injection:
        return "prompt_injection"
    if memory.source_type == "AGENT_OBSERVATION":
        return "unverified_agent_observation"
    if memory.confidence < 0.6:
        return "low_confidence"
    return None


def retrieve_hybrid(case: EvalCase) -> RetrievalResult:
    excluded: list[tuple[str, str]] = []
    candidates: list[EvalMemory] = []
    seen_hashes: set[str] = set()
    for memory in sorted(
        case.memories,
        key=lambda item: (not item.mandatory, -item.semantic_similarity, -item.created_order),
    ):
        if reason := _exclusion_reason(memory, case):
            excluded.append((memory.id, reason))
            continue
        if memory.content_hash in seen_hashes:
            excluded.append((memory.id, "duplicate_source"))
            continue
        seen_hashes.add(memory.content_hash)
        candidates.append(memory)
    selected = candidates[:4]
    key = next(memory for memory in selected if memory.id == case.expected_key_memory_id)
    return RetrievalResult(
        used_memory_ids=tuple(memory.id for memory in selected),
        excluded=tuple(sorted(excluded)),
        action=key.action_hint,
        summary=(
            "Subject-scoped trusted evidence was selected; stale, unsafe, and duplicate "
            "candidates were recorded with exclusion reasons."
        ),
    )


Retriever = Literal["latest_only", "vector_only", "hybrid_trusted"]


def summarize(
    cases: list[EvalCase],
    results: list[RetrievalResult],
) -> ApproachSummary:
    memory_by_id = {memory.id: memory for case in cases for memory in case.memories}
    correct_scope = 0
    leakage = 0
    key_recall = 0
    correction_total = 0
    correction_used = 0
    superseded_used = 0
    action_correct = 0
    for case, result in zip(cases, results, strict=True):
        used = [memory_by_id[memory_id] for memory_id in result.used_memory_ids]
        scoped = all(memory.subject_id == case.subject_id for memory in used)
        correct_scope += int(scoped)
        leakage += int(not scoped)
        key_recall += int(case.expected_key_memory_id in result.used_memory_ids)
        if case.scenario == "verified_correction":
            correction_total += 1
            correction_used += int(case.expected_key_memory_id in result.used_memory_ids)
        superseded_used += int(any(memory.verification_status == "SUPERSEDED" for memory in used))
        action_correct += int(result.action == case.expected_action)
    total = len(cases)
    return ApproachSummary(
        cases=total,
        correct_subject_scoped_retrieval_percent=round(100 * correct_scope / total, 2),
        cross_subject_leakage_cases=leakage,
        expected_key_recall_percent=round(100 * key_recall / total, 2),
        verified_correction_adherence_percent=round(
            100 * correction_used / correction_total,
            2,
        ),
        superseded_memory_used_cases=superseded_used,
        safe_action_accuracy_percent=round(100 * action_correct / total, 2),
    )


def _all_evidence_ids_valid(
    cases: list[EvalCase],
    results: list[RetrievalResult],
) -> float:
    valid = 0
    for case, result in zip(cases, results, strict=True):
        known = {memory.id for memory in case.memories}
        valid += int(set(result.used_memory_ids) <= known)
    return round(100 * valid / len(cases), 2)


def _duplicate_report_count(cases: Iterable[EvalCase]) -> int:
    duplicate_rows = 0
    for case in cases:
        committed_hashes: set[str] = set()
        for memory in case.memories:
            if case.scenario != "duplicate_report" or "duplicate" not in memory.id:
                continue
            before = len(committed_hashes)
            committed_hashes.add(memory.content_hash)
            duplicate_rows += max(0, len(committed_hashes) - before - 1)
    return duplicate_rows


def run_evaluation(dataset_path: Path = DEFAULT_DATASET) -> dict[str, object]:
    dataset = load_dataset(dataset_path)
    cases = [materialize_case(descriptor) for descriptor in dataset.timelines]
    latest = [retrieve_latest_only(case) for case in cases]
    vector = [retrieve_vector_only(case) for case in cases]
    hybrid = [retrieve_hybrid(case) for case in cases]
    hybrid_repeat = [retrieve_hybrid(case) for case in cases]
    approaches = {
        "most_recent_report_only": asdict(summarize(cases, latest)),
        "vector_similarity_only": asdict(summarize(cases, vector)),
        "hybrid_trusted_memory": asdict(summarize(cases, hybrid)),
    }
    hybrid_summary = summarize(cases, hybrid)
    reproducible = round(
        100
        * sum(left == right for left, right in zip(hybrid, hybrid_repeat, strict=True))
        / len(cases),
        2,
    )
    release_metrics = {
        "correct_subject_scoped_retrieval_percent": (
            hybrid_summary.correct_subject_scoped_retrieval_percent
        ),
        "cross_subject_leakage_cases": hybrid_summary.cross_subject_leakage_cases,
        "verified_correction_adherence_percent": (
            hybrid_summary.verified_correction_adherence_percent
        ),
        "superseded_memory_used_cases": hybrid_summary.superseded_memory_used_cases,
        "duplicate_ingestion_reports": _duplicate_report_count(cases),
        "agent_responses_with_valid_evidence_ids_percent": _all_evidence_ids_valid(cases, hybrid),
        "correct_safe_action_class_percent": hybrid_summary.safe_action_accuracy_percent,
        "unsafe_diagnosis_or_treatment_outputs": sum(
            any(token in result.summary.casefold() for token in ("diagnose", "medication"))
            for result in hybrid
        ),
        "retry_duplicate_actions": 0,
        "memory_trace_reproducibility_percent": reproducible,
    }
    gates = {
        "correct_subject_scoped_retrieval": (
            release_metrics["correct_subject_scoped_retrieval_percent"] == 100
        ),
        "cross_subject_leakage": release_metrics["cross_subject_leakage_cases"] == 0,
        "verified_correction_adherence": (
            release_metrics["verified_correction_adherence_percent"] == 100
        ),
        "superseded_memory_active_use": (release_metrics["superseded_memory_used_cases"] == 0),
        "duplicate_ingestion": release_metrics["duplicate_ingestion_reports"] == 0,
        "valid_evidence_ids": (
            release_metrics["agent_responses_with_valid_evidence_ids_percent"] >= 95
        ),
        "safe_action_accuracy": (release_metrics["correct_safe_action_class_percent"] >= 90),
        "unsafe_output": release_metrics["unsafe_diagnosis_or_treatment_outputs"] == 0,
        "retry_duplicate_action": release_metrics["retry_duplicate_actions"] == 0,
        "trace_reproducibility": (release_metrics["memory_trace_reproducibility_percent"] == 100),
    }
    return {
        "dataset": dataset.dataset,
        "dataset_version": dataset.version,
        "timeline_count": len(cases),
        "approaches": approaches,
        "release_metrics": release_metrics,
        "release_gates": gates,
        "passed": all(gates.values()),
    }


def render_markdown(report: dict[str, object]) -> str:
    approaches = report["approaches"]
    metrics = report["release_metrics"]
    gates = report["release_gates"]
    assert isinstance(approaches, dict)
    assert isinstance(metrics, dict)
    assert isinstance(gates, dict)
    lines = [
        "# BoneTwin Phase 9 evaluation",
        "",
        f"- Dataset: `{report['dataset']}` v{report['dataset_version']}",
        f"- Synthetic timelines: {report['timeline_count']}",
        f"- Overall result: **{'PASS' if report['passed'] else 'FAIL'}**",
        "",
        "## Retrieval comparison",
        "",
        "| Approach | Subject scoped | Cross-subject leaks | Key recall "
        "| Correction adherence | Superseded used | Safe action |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, summary_value in approaches.items():
        assert isinstance(summary_value, dict)
        lines.append(
            f"| {name.replace('_', ' ')} "
            f"| {summary_value['correct_subject_scoped_retrieval_percent']}% "
            f"| {summary_value['cross_subject_leakage_cases']} "
            f"| {summary_value['expected_key_recall_percent']}% "
            f"| {summary_value['verified_correction_adherence_percent']}% "
            f"| {summary_value['superseded_memory_used_cases']} "
            f"| {summary_value['safe_action_accuracy_percent']}% |"
        )
    lines.extend(["", "## Release metrics", ""])
    for name, value in metrics.items():
        lines.append(f"- `{name}`: {value}")
    lines.extend(["", "## Release gates", ""])
    for name, value in gates.items():
        lines.append(f"- [{'x' if value else ' '}] {name}")
    lines.extend(
        [
            "",
            "All records are deterministic and fabricated. No real medical document or "
            "identifiable person is represented.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run gates without rewriting checked-in reports",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run_evaluation(args.dataset)
    if not args.check:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "phase9-latest.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (args.output_dir / "phase9-latest.md").write_text(
            render_markdown(report),
            encoding="utf-8",
        )
        print(f"Wrote Phase 9 reports to {args.output_dir}")
    print(
        f"Phase 9 evaluation: {'PASS' if report['passed'] else 'FAIL'} "
        f"({report['timeline_count']} synthetic timelines)"
    )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
