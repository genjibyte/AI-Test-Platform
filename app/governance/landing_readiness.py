"""Landing-readiness rollup for progress and validation planning.

This helper is pure planning data. It consumes caller-supplied label and
manifest-seed metadata, delegates to existing readiness helpers, and grants no
runtime, persistence, headline, verdict, trust, or git authority.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Mapping

from app.governance.project_progress import project_progress_snapshot

LANDING_READINESS_SNAPSHOT_VERSION = "landing_readiness_snapshot.v1"
LANDING_READINESS_BLOCKER_SUMMARY_VERSION = "landing_readiness_blocker_summary.v1"

_PROJECT_STAGES = {
    "foundation_building",
    "core_integration",
    "late_core_harness_hardening_pre_80",
    "landing_validation",
    "release_candidate",
}
_COMPLETION_BANDS = {
    "below_65",
    "around_70",
    "approaching_80",
    "past_80_not_release_ready",
    "near_release",
}
_LANDING_STAGES = {
    "pre_80_landing_readiness_gaps",
    "post_80_needs_landing_evidence",
    "landing_evidence_review_ready",
}
_SOURCE_VERSION_FIELDS = {
    "project_progress",
    "human_label_readiness",
    "golden_defect_denominator",
}
_INPUT_FIELDS = {
    "human_label_rows",
    "human_reviewed_rows",
    "golden_manifest_seed_records",
}
_BLOCKER_FAMILY_ORDER = (
    "project_progress",
    "human_label",
    "golden_defect_denominator",
    "change_batch",
)
_BLOCKER_CLEARANCE_STATUSES = {
    "blocked",
    "evidence_gap",
    "human_review_required",
    "evidence_present",
}
_REVIEW_QUESTION_FAMILY = {
    "api_interface_boundary_review": "project_progress",
    "human_label_calibration_review": "human_label",
    "golden_denominator_owner_gate_review": "golden_defect_denominator",
    "change_batch_review": "change_batch",
}
_EVIDENCE_ITEM_FAMILY = {
    "project_progress_at_least_80": "project_progress",
    "human_disposition_labels": "human_label",
    "human_review_timestamps": "human_label",
    "human_or_verifier_rca": "human_label",
    "misjudgment_reference_labels": "human_label",
    "pinned_defect_denominator": "golden_defect_denominator",
}

_AUTHORITY_FLAGS = {
    "runtime_authority": False,
    "executor_authority": False,
    "dependency_install_allowed": False,
    "pom_mutation_allowed": False,
    "external_execution_allowed": False,
    "dataset_materialization_allowed": False,
    "verifier_execution_allowed": False,
    "model_call_allowed": False,
    "persistence_authority": False,
    "headline_metric_authority": False,
    "git_stage_commit_push_authority": False,
    "digest_authority": False,
    "recommendation_authority": False,
    "verdict_authority": False,
    "trusted_authority": False,
}


class LandingReadinessSnapshotValidationError(ValueError):
    """Raised when a landing-readiness snapshot violates S6 boundary rules."""


class LandingReadinessBlockerSummaryValidationError(ValueError):
    """Raised when a blocker-family summary violates S6 boundary rules."""


def landing_readiness_snapshot(
    labels_or_projections: Iterable[Mapping[str, Any]] = (),
    golden_manifest_seeds: Iterable[Mapping[str, Any]] = (),
    *,
    progress_overrides: Mapping[str, int | float] | None = None,
) -> dict[str, Any]:
    """Return a compact landing-readiness rollup.

    ``progress_overrides`` is forwarded only to
    ``project_progress_snapshot(...)`` for scenario planning. This function
    never reads workspace state, materializes datasets, executes verifiers, or
    promotes metric values to headline claims.
    """
    from app.benchmark.manifest_governance import (
        golden_defect_denominator_readiness,
    )
    from app.benchmark.validation_line import human_label_metric_readiness

    progress = project_progress_snapshot(progress_overrides)
    label_readiness = human_label_metric_readiness(labels_or_projections)
    denominator_readiness = golden_defect_denominator_readiness(
        golden_manifest_seeds
    )
    blockers = _landing_blockers(
        progress=progress,
        label_readiness=label_readiness,
        denominator_readiness=denominator_readiness,
    )
    review_questions = _review_questions(blockers)
    evidence_checklist = _evidence_checklist(
        blockers=blockers,
        label_readiness=label_readiness,
        denominator_readiness=denominator_readiness,
    )

    return {
        "schema_version": LANDING_READINESS_SNAPSHOT_VERSION,
        "advisory": True,
        "report_only": True,
        "overall_completion_percent": progress["overall_completion_percent"],
        "completion_band": progress["completion_band"],
        "project_stage": progress["stage"],
        "landing_stage": _landing_stage(progress, blockers),
        "ready_for_80_stage": (
            progress["overall_completion_percent"] >= 80 and not blockers
        ),
        "ready_for_landing_claims": False,
        "source_versions": {
            "project_progress": progress["schema_version"],
            "human_label_readiness": label_readiness["schema_version"],
            "golden_defect_denominator": denominator_readiness["schema_version"],
        },
        "inputs": {
            "human_label_rows": label_readiness["total_label_rows"],
            "human_reviewed_rows": label_readiness["human_reviewed_rows"],
            "golden_manifest_seed_records": (
                denominator_readiness["total_seed_records"]
            ),
        },
        "human_ready_metric_names": _human_ready_metric_names(label_readiness),
        "human_ready_metric_count": label_readiness["ready_metric_count"],
        "future_defect_denominator_possible": (
            denominator_readiness["future_defect_denominator_possible"]
        ),
        "defect_denominator_ready_now": (
            denominator_readiness["defect_denominator_ready_now"]
        ),
        "landing_blockers": blockers,
        "next_best_steps": _next_best_steps(blockers),
        "review_questions": review_questions,
        "evidence_checklist": evidence_checklist,
        "progress": {
            "schema_version": progress["schema_version"],
            "stage": progress["stage"],
            "overall_completion_percent": progress[
                "overall_completion_percent"
            ],
            "completion_band": progress["completion_band"],
            "not_80_yet_because": list(progress["not_80_yet_because"]),
        },
        "human_label_readiness": label_readiness,
        "golden_defect_denominator_readiness": denominator_readiness,
        "red_lines": [
            "do not promote readiness values to headline claims",
            "do not materialize datasets or execute verifiers from metadata",
            "do not change conclusion=NEED_HUMAN_REVIEW or trusted=False",
            "do not stage, commit, or push from the landing-readiness path",
        ],
        **_AUTHORITY_FLAGS,
        "note": (
            "Landing readiness is a planning rollup over existing pure helpers. "
            "It does not approve release readiness, headline metrics, dataset "
            "materialization, executor work, verdict changes, or trusted=True."
        ),
    }


def validate_landing_readiness_snapshot(
    snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate a ``landing_readiness_snapshot.v1`` mapping.

    This is a pure structural and authority-boundary check. It does not
    recompute readiness, read workspace state, execute verifiers, persist labels,
    or promote anything to release/headline/verdict authority.
    """
    if not isinstance(snapshot, Mapping):
        raise LandingReadinessSnapshotValidationError(
            "landing readiness snapshot must be a mapping"
        )
    if snapshot.get("schema_version") != LANDING_READINESS_SNAPSHOT_VERSION:
        raise LandingReadinessSnapshotValidationError(
            "unsupported landing readiness snapshot schema_version"
        )

    required_fields = {
        "schema_version",
        "advisory",
        "report_only",
        "overall_completion_percent",
        "completion_band",
        "project_stage",
        "landing_stage",
        "ready_for_80_stage",
        "ready_for_landing_claims",
        "source_versions",
        "inputs",
        "human_ready_metric_names",
        "human_ready_metric_count",
        "future_defect_denominator_possible",
        "defect_denominator_ready_now",
        "landing_blockers",
        "next_best_steps",
        "review_questions",
        "evidence_checklist",
        "progress",
        "human_label_readiness",
        "golden_defect_denominator_readiness",
        "red_lines",
        "note",
        *set(_AUTHORITY_FLAGS),
    }
    missing = sorted(field for field in required_fields if field not in snapshot)
    if missing:
        raise LandingReadinessSnapshotValidationError(
            "landing readiness snapshot missing fields: " + ", ".join(missing)
        )

    if snapshot.get("advisory") is not True or snapshot.get("report_only") is not True:
        raise LandingReadinessSnapshotValidationError(
            "landing readiness snapshot must stay advisory and report_only"
        )
    if snapshot.get("ready_for_landing_claims") is not False:
        raise LandingReadinessSnapshotValidationError(
            "landing readiness snapshot must not approve landing claims"
        )
    _validate_percent(
        snapshot.get("overall_completion_percent"),
        "overall_completion_percent",
    )
    _validate_enum(
        snapshot.get("completion_band"),
        _COMPLETION_BANDS,
        "completion_band",
    )
    _validate_enum(snapshot.get("project_stage"), _PROJECT_STAGES, "project_stage")
    _validate_enum(snapshot.get("landing_stage"), _LANDING_STAGES, "landing_stage")
    _validate_bool(snapshot.get("ready_for_80_stage"), "ready_for_80_stage")
    _validate_bool(
        snapshot.get("future_defect_denominator_possible"),
        "future_defect_denominator_possible",
    )
    _validate_bool(
        snapshot.get("defect_denominator_ready_now"),
        "defect_denominator_ready_now",
    )
    _require_authority_flags_false(snapshot, _AUTHORITY_FLAGS)
    source_versions = _require_mapping(snapshot.get("source_versions"), "source_versions")
    inputs = _require_mapping(snapshot.get("inputs"), "inputs")
    progress = _require_mapping(snapshot.get("progress"), "progress")
    human_readiness = _require_mapping(
        snapshot.get("human_label_readiness"),
        "human_label_readiness",
    )
    denominator_readiness = _require_mapping(
        snapshot.get("golden_defect_denominator_readiness"),
        "golden_defect_denominator_readiness",
    )
    _validate_source_versions(
        source_versions,
        progress=progress,
        human_readiness=human_readiness,
        denominator_readiness=denominator_readiness,
    )
    _validate_inputs(inputs)
    _validate_progress_projection(progress, snapshot)
    ready_metrics = _require_list(
        snapshot.get("human_ready_metric_names"),
        "human_ready_metric_names",
    )
    ready_metric_count = _validate_nonnegative_int(
        snapshot.get("human_ready_metric_count"),
        "human_ready_metric_count",
    )
    if ready_metric_count != len(ready_metrics):
        raise LandingReadinessSnapshotValidationError(
            "human_ready_metric_count must match human_ready_metric_names length"
        )
    landing_blockers = _require_string_list(
        snapshot.get("landing_blockers"),
        "landing_blockers",
    )
    next_best_steps = _require_string_list(
        snapshot.get("next_best_steps"),
        "next_best_steps",
    )
    review_questions = _validate_review_questions(snapshot.get("review_questions"))
    evidence_checklist = _validate_evidence_checklist(
        snapshot.get("evidence_checklist")
    )
    _require_string_list(snapshot.get("red_lines"), "red_lines")
    _require_nested_false(human_readiness, "headline_metric_authority")
    _require_nested_false(human_readiness, "persistence_authority")
    _require_nested_false(human_readiness, "digest_authority")
    _require_nested_false(human_readiness, "verdict_authority")
    _require_nested_false(human_readiness, "trusted_authority")
    _require_nested_false(
        denominator_readiness,
        "dataset_materialization_allowed_now",
    )
    _require_nested_false(denominator_readiness, "download_allowed_now")
    _require_nested_false(denominator_readiness, "external_execution_allowed_now")
    _require_nested_false(denominator_readiness, "verifier_execution_allowed_now")
    _require_nested_false(denominator_readiness, "benchmark_headline_allowed_now")
    _require_nested_false(denominator_readiness, "defect_discovery_rate_authority")
    _require_nested_false(denominator_readiness, "verdict_authority")
    _require_nested_false(denominator_readiness, "trusted_authority")
    _validate_derived_consistency(
        snapshot=snapshot,
        progress=progress,
        human_readiness=human_readiness,
        denominator_readiness=denominator_readiness,
        inputs=inputs,
        landing_blockers=landing_blockers,
        next_best_steps=next_best_steps,
        review_questions=review_questions,
        evidence_checklist=evidence_checklist,
    )

    return dict(snapshot)


def landing_readiness_blocker_summary(
    snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    """Return a blocker-family summary over an existing readiness snapshot.

    The input snapshot is validated first. The returned projection is only a
    human-review planning aid; it does not recompute readiness from workspace
    state, collect labels, materialize datasets, execute verifiers, or grant any
    headline/verdict/trust authority.
    """
    normalized = validate_landing_readiness_snapshot(snapshot)
    blockers = list(normalized["landing_blockers"])
    questions = list(normalized["review_questions"])
    checklist = list(normalized["evidence_checklist"])

    grouped_blockers: dict[str, list[str]] = {
        family: [] for family in _BLOCKER_FAMILY_ORDER
    }
    grouped_blockers["other"] = []
    for blocker in blockers:
        grouped_blockers.setdefault(_blocker_family(blocker), []).append(blocker)

    families = [
        _blocker_family_row(
            family=family,
            blockers=grouped_blockers.get(family, []),
            questions=questions,
            checklist=checklist,
        )
        for family in _BLOCKER_FAMILY_ORDER
    ]
    if grouped_blockers["other"]:
        families.append(
            _blocker_family_row(
                family="other",
                blockers=grouped_blockers["other"],
                questions=questions,
                checklist=checklist,
            )
        )

    actionable = [
        row["family"]
        for row in families
        if row["clearance_status"] in {"blocked", "evidence_gap", "human_review_required"}
    ]

    return {
        "schema_version": LANDING_READINESS_BLOCKER_SUMMARY_VERSION,
        "advisory": True,
        "report_only": True,
        "source_schema_version": normalized["schema_version"],
        "landing_stage": normalized["landing_stage"],
        "ready_for_80_stage": normalized["ready_for_80_stage"],
        "ready_for_landing_claims": False,
        "total_blockers": len(blockers),
        "family_counts": {
            family: len(grouped_blockers.get(family, []))
            for family in _BLOCKER_FAMILY_ORDER
        },
        "evidence_status_counts": dict(Counter(
            str(item.get("current_status") or "missing") for item in checklist
        )),
        "next_clearance_family": actionable[0] if actionable else None,
        "families": families,
        "red_lines": [
            "do not treat blocker grouping as release approval",
            "do not collect or persist evidence from blocker summary",
            "do not materialize datasets or execute verifiers from blocker summary",
            "do not change conclusion=NEED_HUMAN_REVIEW or trusted=False",
        ],
        **_AUTHORITY_FLAGS,
        "note": (
            "Blocker summary is a derived planning view over one validated "
            "landing-readiness snapshot. It is not a metric, release gate, "
            "executor plan, dataset approval, verdict, or trust signal."
        ),
    }


def validate_landing_readiness_blocker_summary(
    summary: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate a ``landing_readiness_blocker_summary.v1`` mapping.

    This validates a precomputed summary as a handoff artifact. It does not
    recompute the source snapshot, read workspace state, collect evidence,
    materialize datasets, execute verifiers, or promote the summary to any
    headline/verdict/trust authority.
    """
    if not isinstance(summary, Mapping):
        raise LandingReadinessBlockerSummaryValidationError(
            "landing readiness blocker summary must be a mapping"
        )
    if summary.get("schema_version") != LANDING_READINESS_BLOCKER_SUMMARY_VERSION:
        raise LandingReadinessBlockerSummaryValidationError(
            "unsupported landing readiness blocker summary schema_version"
        )

    required_fields = {
        "schema_version",
        "advisory",
        "report_only",
        "source_schema_version",
        "landing_stage",
        "ready_for_80_stage",
        "ready_for_landing_claims",
        "total_blockers",
        "family_counts",
        "evidence_status_counts",
        "next_clearance_family",
        "families",
        "red_lines",
        "note",
        *set(_AUTHORITY_FLAGS),
    }
    missing = sorted(field for field in required_fields if field not in summary)
    if missing:
        raise LandingReadinessBlockerSummaryValidationError(
            "landing readiness blocker summary missing fields: "
            + ", ".join(missing)
        )

    if summary.get("advisory") is not True or summary.get("report_only") is not True:
        raise LandingReadinessBlockerSummaryValidationError(
            "landing readiness blocker summary must stay advisory and report_only"
        )
    if summary.get("source_schema_version") != LANDING_READINESS_SNAPSHOT_VERSION:
        raise LandingReadinessBlockerSummaryValidationError(
            "source_schema_version must match landing readiness snapshot schema"
        )
    _validate_enum_for_blocker_summary(
        summary.get("landing_stage"),
        _LANDING_STAGES,
        "landing_stage",
    )
    _validate_bool_for_blocker_summary(
        summary.get("ready_for_80_stage"),
        "ready_for_80_stage",
    )
    if summary.get("ready_for_landing_claims") is not False:
        raise LandingReadinessBlockerSummaryValidationError(
            "landing readiness blocker summary must not approve landing claims"
        )

    _require_authority_flags_false_for_blocker_summary(summary, _AUTHORITY_FLAGS)
    total_blockers = _validate_nonnegative_int_for_blocker_summary(
        summary.get("total_blockers"),
        "total_blockers",
    )
    family_counts = _require_mapping_for_blocker_summary(
        summary.get("family_counts"),
        "family_counts",
    )
    evidence_status_counts = _require_mapping_for_blocker_summary(
        summary.get("evidence_status_counts"),
        "evidence_status_counts",
    )
    families = _validate_blocker_summary_families(summary.get("families"))
    _validate_blocker_summary_counts(
        total_blockers=total_blockers,
        family_counts=family_counts,
        evidence_status_counts=evidence_status_counts,
        families=families,
    )
    _validate_next_clearance_family(
        summary.get("next_clearance_family"),
        families=families,
    )
    _require_string_list_for_blocker_summary(summary.get("red_lines"), "red_lines")
    return dict(summary)


def _human_ready_metric_names(label_readiness: Mapping[str, Any]) -> list[str]:
    metrics = label_readiness.get("metrics") or {}
    return [
        name
        for name, metric in metrics.items()
        if isinstance(metric, Mapping)
        and metric.get("status") == "available_from_supplied_labels"
    ]


def _landing_blockers(
    *,
    progress: Mapping[str, Any],
    label_readiness: Mapping[str, Any],
    denominator_readiness: Mapping[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if int(progress.get("overall_completion_percent") or 0) < 80:
        blockers.append("project_completion_below_80")
    blockers.extend(
        f"human_label:{reason}"
        for reason in label_readiness.get("not_ready_reasons", [])
    )
    blockers.extend(
        f"golden_defect_denominator:{reason}"
        for reason in denominator_readiness.get("not_ready_reasons", [])
    )
    if denominator_readiness.get("defect_denominator_ready_now") is not True:
        blockers.append("golden_defect_denominator:not_ready_now")
    return _dedupe(blockers)


def _landing_stage(
    progress: Mapping[str, Any],
    blockers: list[str],
) -> str:
    if int(progress.get("overall_completion_percent") or 0) < 80:
        return "pre_80_landing_readiness_gaps"
    if blockers:
        return "post_80_needs_landing_evidence"
    return "landing_evidence_review_ready"


def _next_best_steps(blockers: list[str]) -> list[str]:
    steps: list[str] = []
    blocker_set = set(blockers)
    if "project_completion_below_80" in blocker_set:
        steps.append("stabilize API/interface report boundaries before executor design")
    if any(item.startswith("human_label:") for item in blocker_set):
        steps.append("supply calibrated human-review labels for landing metrics")
    if any(item.startswith("golden_defect_denominator:") for item in blocker_set):
        steps.append("prepare owner-gated Golden Set dataset-slice and verifier design")
    steps.append("keep current large change set in human-reviewed batches")
    return _dedupe(steps)


def _review_questions(blockers: list[str]) -> list[dict[str, Any]]:
    questions: list[dict[str, Any]] = []
    blocker_set = set(blockers)
    if "project_completion_below_80" in blocker_set:
        questions.append({
            "id": "api_interface_boundary_review",
            "question": (
                "Which API/interface evidence boundary must stabilize before "
                "owner-gated executor design?"
            ),
            "triggered_by": ["project_completion_below_80"],
            "owner_decision_required": True,
            "authority": "planning_only",
        })
    human_blockers = [
        blocker for blocker in blockers if blocker.startswith("human_label:")
    ]
    if human_blockers:
        questions.append({
            "id": "human_label_calibration_review",
            "question": (
                "Do supplied labels cover disposition, edit count, timestamps, "
                "RCA, misjudgment, and defect-confirmation needs for the target "
                "landing metrics?"
            ),
            "triggered_by": human_blockers,
            "owner_decision_required": True,
            "authority": "planning_only",
        })
    golden_blockers = [
        blocker
        for blocker in blockers
        if blocker.startswith("golden_defect_denominator:")
    ]
    if golden_blockers:
        questions.append({
            "id": "golden_denominator_owner_gate_review",
            "question": (
                "Which manifest_seed records have pinned defect tasks, and what "
                "owner gate is required before any dataset slice or verifier work?"
            ),
            "triggered_by": golden_blockers,
            "owner_decision_required": True,
            "authority": "planning_only",
        })
    questions.append({
        "id": "change_batch_review",
        "question": (
            "Which current change-set batch should be human-reviewed before "
            "staging this readiness view?"
        ),
        "triggered_by": ["large_dirty_worktree"],
        "owner_decision_required": True,
        "authority": "handoff_only",
    })
    return questions


def _evidence_checklist(
    *,
    blockers: list[str],
    label_readiness: Mapping[str, Any],
    denominator_readiness: Mapping[str, Any],
) -> list[dict[str, Any]]:
    blocker_set = set(blockers)
    human_metrics = label_readiness.get("metrics") or {}
    return [
        {
            "id": "project_progress_at_least_80",
            "required_evidence": "project_progress_snapshot.overall_completion_percent >= 80",
            "current_status": (
                "missing" if "project_completion_below_80" in blocker_set else "present"
            ),
            "authority": "planning_only",
        },
        {
            "id": "human_disposition_labels",
            "required_evidence": "HumanReviewLabel.disposition for reviewed candidates",
            "current_status": _metric_status(human_metrics, "usable_test_rate"),
            "authority": "metric_readiness_only",
        },
        {
            "id": "human_review_timestamps",
            "required_evidence": "review_started_at and review_completed_at",
            "current_status": _metric_status(human_metrics, "human_handling_time"),
            "authority": "metric_readiness_only",
        },
        {
            "id": "human_or_verifier_rca",
            "required_evidence": "root_cause evidence plus future failure-first timestamp",
            "current_status": _metric_status(human_metrics, "diagnosis_time"),
            "authority": "metric_readiness_only",
        },
        {
            "id": "misjudgment_reference_labels",
            "required_evidence": "misjudgment.kind labels compared with platform signals",
            "current_status": _metric_status(human_metrics, "misjudgment_rate"),
            "authority": "metric_readiness_only",
        },
        {
            "id": "pinned_defect_denominator",
            "required_evidence": "metadata-only manifest_seed now; owner-gated dataset/verifier later",
            "current_status": (
                "future_owner_gated"
                if denominator_readiness.get("future_defect_denominator_possible")
                else "missing"
            ),
            "authority": "metadata_only",
        },
    ]


def _metric_status(metrics: Mapping[str, Any], metric: str) -> str:
    value = metrics.get(metric)
    if not isinstance(value, Mapping):
        return "missing"
    status = str(value.get("status") or "missing")
    if status == "available_from_supplied_labels":
        return "present"
    return status


def _require_authority_flags_false(
    snapshot: Mapping[str, Any],
    flags: Mapping[str, bool],
) -> None:
    for field in flags:
        if snapshot.get(field) is not False:
            raise LandingReadinessSnapshotValidationError(
                f"landing readiness snapshot authority flag must be false: {field}"
            )


def _validate_percent(value: Any, field: str) -> int:
    percent = _validate_nonnegative_int(value, field)
    if percent > 100:
        raise LandingReadinessSnapshotValidationError(
            f"{field} must be between 0 and 100"
        )
    return percent


def _validate_nonnegative_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise LandingReadinessSnapshotValidationError(
            f"{field} must be a non-negative integer"
        )
    if value < 0:
        raise LandingReadinessSnapshotValidationError(
            f"{field} must be a non-negative integer"
        )
    return value


def _validate_bool(value: Any, field: str) -> None:
    if not isinstance(value, bool):
        raise LandingReadinessSnapshotValidationError(f"{field} must be a boolean")


def _validate_enum(value: Any, allowed: set[str], field: str) -> None:
    if value not in allowed:
        raise LandingReadinessSnapshotValidationError(f"{field} is not allowed")


def _validate_source_versions(
    value: Mapping[str, Any],
    *,
    progress: Mapping[str, Any],
    human_readiness: Mapping[str, Any],
    denominator_readiness: Mapping[str, Any],
) -> None:
    missing = sorted(field for field in _SOURCE_VERSION_FIELDS if field not in value)
    if missing:
        raise LandingReadinessSnapshotValidationError(
            "source_versions missing fields: " + ", ".join(missing)
        )
    for field in _SOURCE_VERSION_FIELDS:
        if not isinstance(value.get(field), str) or not value.get(field):
            raise LandingReadinessSnapshotValidationError(
                f"source_versions.{field} must be a non-empty string"
            )
    expected = {
        "project_progress": progress.get("schema_version"),
        "human_label_readiness": human_readiness.get("schema_version"),
        "golden_defect_denominator": denominator_readiness.get("schema_version"),
    }
    for field, expected_value in expected.items():
        if value.get(field) != expected_value:
            raise LandingReadinessSnapshotValidationError(
                f"source_versions.{field} must match nested schema_version"
            )


def _validate_inputs(value: Mapping[str, Any]) -> None:
    missing = sorted(field for field in _INPUT_FIELDS if field not in value)
    if missing:
        raise LandingReadinessSnapshotValidationError(
            "inputs missing fields: " + ", ".join(missing)
        )
    for field in _INPUT_FIELDS:
        _validate_nonnegative_int(value.get(field), f"inputs.{field}")


def _validate_progress_projection(
    progress: Mapping[str, Any],
    snapshot: Mapping[str, Any],
) -> None:
    for field in ("schema_version", "stage", "overall_completion_percent", "completion_band"):
        if field not in progress:
            raise LandingReadinessSnapshotValidationError(
                f"progress missing {field}"
            )
    _validate_percent(
        progress.get("overall_completion_percent"),
        "progress.overall_completion_percent",
    )
    _validate_enum(progress.get("stage"), _PROJECT_STAGES, "progress.stage")
    _validate_enum(
        progress.get("completion_band"),
        _COMPLETION_BANDS,
        "progress.completion_band",
    )
    _require_list(progress.get("not_80_yet_because"), "progress.not_80_yet_because")
    if progress.get("overall_completion_percent") != snapshot.get(
        "overall_completion_percent"
    ):
        raise LandingReadinessSnapshotValidationError(
            "progress.overall_completion_percent must match top-level value"
        )
    if progress.get("stage") != snapshot.get("project_stage"):
        raise LandingReadinessSnapshotValidationError(
            "progress.stage must match project_stage"
        )
    if progress.get("completion_band") != snapshot.get("completion_band"):
        raise LandingReadinessSnapshotValidationError(
            "progress.completion_band must match top-level value"
        )


def _require_nested_false(value: Mapping[str, Any], field: str) -> None:
    if value.get(field) is not False:
        raise LandingReadinessSnapshotValidationError(
            f"landing readiness nested authority flag must be false: {field}"
        )


def _require_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise LandingReadinessSnapshotValidationError(f"{field} must be a mapping")
    return value


def _require_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise LandingReadinessSnapshotValidationError(f"{field} must be a list")
    return value


def _require_string_list(value: Any, field: str) -> list[str]:
    items = _require_list(value, field)
    normalized: list[str] = []
    for index, item in enumerate(items):
        if not isinstance(item, str) or not item.strip():
            raise LandingReadinessSnapshotValidationError(
                f"{field}[{index}] must be a non-empty string"
            )
        normalized.append(item)
    return normalized


def _validate_non_empty_str(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LandingReadinessSnapshotValidationError(
            f"{field} must be a non-empty string"
        )
    return value


def _validate_review_questions(value: Any) -> list[Mapping[str, Any]]:
    questions = _require_list(value, "review_questions")
    normalized: list[Mapping[str, Any]] = []
    for index, question in enumerate(questions):
        if not isinstance(question, Mapping):
            raise LandingReadinessSnapshotValidationError(
                f"review_questions[{index}] must be a mapping"
            )
        for field in (
            "id",
            "question",
            "triggered_by",
            "owner_decision_required",
            "authority",
        ):
            if field not in question:
                raise LandingReadinessSnapshotValidationError(
                    f"review_questions[{index}] missing {field}"
                )
        _validate_non_empty_str(question.get("id"), f"review_questions[{index}].id")
        _validate_non_empty_str(
            question.get("question"),
            f"review_questions[{index}].question",
        )
        _require_string_list(
            question.get("triggered_by"),
            f"review_questions[{index}].triggered_by",
        )
        _validate_bool(
            question.get("owner_decision_required"),
            f"review_questions[{index}].owner_decision_required",
        )
        if question.get("authority") not in {"planning_only", "handoff_only"}:
            raise LandingReadinessSnapshotValidationError(
                f"review_questions[{index}].authority is not allowed"
            )
        normalized.append(question)
    return normalized


def _validate_evidence_checklist(value: Any) -> list[Mapping[str, Any]]:
    checklist = _require_list(value, "evidence_checklist")
    allowed_authority = {"planning_only", "metric_readiness_only", "metadata_only"}
    normalized: list[Mapping[str, Any]] = []
    for index, item in enumerate(checklist):
        if not isinstance(item, Mapping):
            raise LandingReadinessSnapshotValidationError(
                f"evidence_checklist[{index}] must be a mapping"
            )
        for field in ("id", "required_evidence", "current_status", "authority"):
            if field not in item:
                raise LandingReadinessSnapshotValidationError(
                    f"evidence_checklist[{index}] missing {field}"
                )
        _validate_non_empty_str(item.get("id"), f"evidence_checklist[{index}].id")
        _validate_non_empty_str(
            item.get("required_evidence"),
            f"evidence_checklist[{index}].required_evidence",
        )
        _validate_non_empty_str(
            item.get("current_status"),
            f"evidence_checklist[{index}].current_status",
        )
        if item.get("authority") not in allowed_authority:
            raise LandingReadinessSnapshotValidationError(
                f"evidence_checklist[{index}].authority is not allowed"
            )
        normalized.append(item)
    return normalized


def _validate_derived_consistency(
    *,
    snapshot: Mapping[str, Any],
    progress: Mapping[str, Any],
    human_readiness: Mapping[str, Any],
    denominator_readiness: Mapping[str, Any],
    inputs: Mapping[str, Any],
    landing_blockers: list[str],
    next_best_steps: list[str],
    review_questions: list[Mapping[str, Any]],
    evidence_checklist: list[Mapping[str, Any]],
) -> None:
    _require_mapping(human_readiness.get("metrics"), "human_label_readiness.metrics")
    _require_string_list(
        human_readiness.get("not_ready_reasons"),
        "human_label_readiness.not_ready_reasons",
    )
    _require_string_list(
        denominator_readiness.get("not_ready_reasons"),
        "golden_defect_denominator_readiness.not_ready_reasons",
    )
    future_defect_denominator_possible = denominator_readiness.get(
        "future_defect_denominator_possible"
    )
    _validate_bool(
        future_defect_denominator_possible,
        "golden_defect_denominator_readiness.future_defect_denominator_possible",
    )
    defect_denominator_ready_now = denominator_readiness.get(
        "defect_denominator_ready_now"
    )
    _validate_bool(
        defect_denominator_ready_now,
        "golden_defect_denominator_readiness.defect_denominator_ready_now",
    )
    expected_blockers = _landing_blockers(
        progress=progress,
        label_readiness=human_readiness,
        denominator_readiness=denominator_readiness,
    )
    if landing_blockers != expected_blockers:
        raise LandingReadinessSnapshotValidationError(
            "landing_blockers must match progress, human label readiness, "
            "and golden denominator readiness"
        )

    expected_steps = _next_best_steps(landing_blockers)
    if next_best_steps != expected_steps:
        raise LandingReadinessSnapshotValidationError(
            "next_best_steps must match landing_blockers"
        )

    expected_stage = _landing_stage(progress, landing_blockers)
    if snapshot.get("landing_stage") != expected_stage:
        raise LandingReadinessSnapshotValidationError(
            "landing_stage must match percent and blockers"
        )

    progress_percent = _validate_percent(
        progress.get("overall_completion_percent"),
        "progress.overall_completion_percent",
    )
    expected_ready_for_80 = progress_percent >= 80 and not landing_blockers
    if snapshot.get("ready_for_80_stage") is not expected_ready_for_80:
        raise LandingReadinessSnapshotValidationError(
            "ready_for_80_stage must match percent and blockers"
        )

    _validate_count_match(
        actual=inputs.get("human_label_rows"),
        expected=human_readiness.get("total_label_rows"),
        field="inputs.human_label_rows",
        expected_field="human_label_readiness.total_label_rows",
    )
    _validate_count_match(
        actual=inputs.get("human_reviewed_rows"),
        expected=human_readiness.get("human_reviewed_rows"),
        field="inputs.human_reviewed_rows",
        expected_field="human_label_readiness.human_reviewed_rows",
    )
    _validate_count_match(
        actual=inputs.get("golden_manifest_seed_records"),
        expected=denominator_readiness.get("total_seed_records"),
        field="inputs.golden_manifest_seed_records",
        expected_field="golden_defect_denominator_readiness.total_seed_records",
    )

    expected_metric_names = _human_ready_metric_names(human_readiness)
    if snapshot.get("human_ready_metric_names") != expected_metric_names:
        raise LandingReadinessSnapshotValidationError(
            "human_ready_metric_names must match human_label_readiness metrics"
        )
    nested_ready_metric_count = _validate_nonnegative_int(
        human_readiness.get("ready_metric_count"),
        "human_label_readiness.ready_metric_count",
    )
    if snapshot.get("human_ready_metric_count") != nested_ready_metric_count:
        raise LandingReadinessSnapshotValidationError(
            "human_ready_metric_count must match human_label_readiness.ready_metric_count"
        )
    if nested_ready_metric_count != len(expected_metric_names):
        raise LandingReadinessSnapshotValidationError(
            "human_label_readiness.ready_metric_count must match ready metric names length"
        )

    if snapshot.get(
        "future_defect_denominator_possible"
    ) is not future_defect_denominator_possible:
        raise LandingReadinessSnapshotValidationError(
            "future_defect_denominator_possible must match denominator readiness"
        )
    if snapshot.get("defect_denominator_ready_now") is not defect_denominator_ready_now:
        raise LandingReadinessSnapshotValidationError(
            "defect_denominator_ready_now must match denominator readiness"
        )

    expected_questions = _review_question_fingerprint_list(
        _review_questions(landing_blockers)
    )
    if _review_question_fingerprint_list(review_questions) != expected_questions:
        raise LandingReadinessSnapshotValidationError(
            "review_questions must match landing_blockers"
        )

    expected_checklist = _evidence_checklist_fingerprint_list(
        _evidence_checklist(
            blockers=landing_blockers,
            label_readiness=human_readiness,
            denominator_readiness=denominator_readiness,
        )
    )
    if _evidence_checklist_fingerprint_list(evidence_checklist) != expected_checklist:
        raise LandingReadinessSnapshotValidationError(
            "evidence_checklist must match landing readiness inputs"
        )


def _validate_count_match(
    *,
    actual: Any,
    expected: Any,
    field: str,
    expected_field: str,
) -> None:
    actual_count = _validate_nonnegative_int(actual, field)
    expected_count = _validate_nonnegative_int(expected, expected_field)
    if actual_count != expected_count:
        raise LandingReadinessSnapshotValidationError(
            f"{field} must match {expected_field}"
        )


def _review_question_fingerprint_list(
    questions: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "id": question.get("id"),
            "triggered_by": list(question.get("triggered_by") or []),
            "owner_decision_required": question.get("owner_decision_required"),
            "authority": question.get("authority"),
        }
        for question in questions
    ]


def _evidence_checklist_fingerprint_list(
    checklist: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "id": item.get("id"),
            "current_status": item.get("current_status"),
            "authority": item.get("authority"),
        }
        for item in checklist
    ]


def _blocker_family(blocker: str) -> str:
    if blocker == "project_completion_below_80":
        return "project_progress"
    if blocker.startswith("human_label:"):
        return "human_label"
    if blocker.startswith("golden_defect_denominator:"):
        return "golden_defect_denominator"
    return "other"


def _blocker_family_row(
    *,
    family: str,
    blockers: list[str],
    questions: list[Mapping[str, Any]],
    checklist: list[Mapping[str, Any]],
) -> dict[str, Any]:
    question_ids = [
        str(question.get("id"))
        for question in questions
        if _REVIEW_QUESTION_FAMILY.get(str(question.get("id"))) == family
    ]
    evidence_items = [
        item
        for item in checklist
        if _EVIDENCE_ITEM_FAMILY.get(str(item.get("id"))) == family
    ]
    evidence_item_ids = [str(item.get("id")) for item in evidence_items]
    non_present_evidence_ids = [
        str(item.get("id"))
        for item in evidence_items
        if item.get("current_status") != "present"
    ]

    if blockers:
        clearance_status = "blocked"
    elif family == "change_batch":
        clearance_status = "human_review_required"
    elif non_present_evidence_ids:
        clearance_status = "evidence_gap"
    else:
        clearance_status = "evidence_present"

    return {
        "family": family,
        "blocker_count": len(blockers),
        "blockers": list(blockers),
        "review_question_ids": question_ids,
        "evidence_item_ids": evidence_item_ids,
        "non_present_evidence_item_ids": non_present_evidence_ids,
        "owner_decision_required": bool(question_ids),
        "clearance_status": clearance_status,
        "authority": "planning_only",
    }


def _require_mapping_for_blocker_summary(
    value: Any,
    field: str,
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise LandingReadinessBlockerSummaryValidationError(
            f"{field} must be a mapping"
        )
    return value


def _require_list_for_blocker_summary(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise LandingReadinessBlockerSummaryValidationError(f"{field} must be a list")
    return value


def _require_string_list_for_blocker_summary(
    value: Any,
    field: str,
) -> list[str]:
    items = _require_list_for_blocker_summary(value, field)
    normalized: list[str] = []
    for index, item in enumerate(items):
        if not isinstance(item, str) or not item.strip():
            raise LandingReadinessBlockerSummaryValidationError(
                f"{field}[{index}] must be a non-empty string"
            )
        normalized.append(item)
    return normalized


def _validate_nonnegative_int_for_blocker_summary(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise LandingReadinessBlockerSummaryValidationError(
            f"{field} must be a non-negative integer"
        )
    if value < 0:
        raise LandingReadinessBlockerSummaryValidationError(
            f"{field} must be a non-negative integer"
        )
    return value


def _validate_bool_for_blocker_summary(value: Any, field: str) -> None:
    if not isinstance(value, bool):
        raise LandingReadinessBlockerSummaryValidationError(
            f"{field} must be a boolean"
        )


def _validate_enum_for_blocker_summary(
    value: Any,
    allowed: set[str],
    field: str,
) -> None:
    if value not in allowed:
        raise LandingReadinessBlockerSummaryValidationError(
            f"{field} is not allowed"
        )


def _require_authority_flags_false_for_blocker_summary(
    summary: Mapping[str, Any],
    flags: Mapping[str, bool],
) -> None:
    for field in flags:
        if summary.get(field) is not False:
            raise LandingReadinessBlockerSummaryValidationError(
                "landing readiness blocker summary authority flag must be false: "
                + field
            )


def _validate_blocker_summary_families(value: Any) -> list[Mapping[str, Any]]:
    families = _require_list_for_blocker_summary(value, "families")
    normalized: list[Mapping[str, Any]] = []
    seen: set[str] = set()
    for index, row in enumerate(families):
        if not isinstance(row, Mapping):
            raise LandingReadinessBlockerSummaryValidationError(
                f"families[{index}] must be a mapping"
            )
        for field in (
            "family",
            "blocker_count",
            "blockers",
            "review_question_ids",
            "evidence_item_ids",
            "non_present_evidence_item_ids",
            "owner_decision_required",
            "clearance_status",
            "authority",
        ):
            if field not in row:
                raise LandingReadinessBlockerSummaryValidationError(
                    f"families[{index}] missing {field}"
                )
        family = _validate_blocker_family_name(row.get("family"), index)
        if family in seen:
            raise LandingReadinessBlockerSummaryValidationError(
                f"families duplicate family: {family}"
            )
        seen.add(family)
        blocker_count = _validate_nonnegative_int_for_blocker_summary(
            row.get("blocker_count"),
            f"families[{index}].blocker_count",
        )
        blockers = _require_string_list_for_blocker_summary(
            row.get("blockers"),
            f"families[{index}].blockers",
        )
        if blocker_count != len(blockers):
            raise LandingReadinessBlockerSummaryValidationError(
                f"families[{index}].blocker_count must match blockers length"
            )
        review_question_ids = _require_string_list_for_blocker_summary(
            row.get("review_question_ids"),
            f"families[{index}].review_question_ids",
        )
        evidence_item_ids = _require_string_list_for_blocker_summary(
            row.get("evidence_item_ids"),
            f"families[{index}].evidence_item_ids",
        )
        non_present_ids = _require_string_list_for_blocker_summary(
            row.get("non_present_evidence_item_ids"),
            f"families[{index}].non_present_evidence_item_ids",
        )
        if not set(non_present_ids).issubset(set(evidence_item_ids)):
            raise LandingReadinessBlockerSummaryValidationError(
                "non_present_evidence_item_ids must be a subset of "
                "evidence_item_ids"
            )
        _validate_bool_for_blocker_summary(
            row.get("owner_decision_required"),
            f"families[{index}].owner_decision_required",
        )
        if row.get("owner_decision_required") is not bool(review_question_ids):
            raise LandingReadinessBlockerSummaryValidationError(
                "owner_decision_required must match review_question_ids presence"
            )
        if row.get("clearance_status") not in _BLOCKER_CLEARANCE_STATUSES:
            raise LandingReadinessBlockerSummaryValidationError(
                f"families[{index}].clearance_status is not allowed"
            )
        if row.get("clearance_status") != _expected_clearance_status(
            family=family,
            blocker_count=blocker_count,
            non_present_evidence_ids=non_present_ids,
        ):
            raise LandingReadinessBlockerSummaryValidationError(
                f"families[{index}].clearance_status must match blockers and evidence"
            )
        if row.get("authority") != "planning_only":
            raise LandingReadinessBlockerSummaryValidationError(
                f"families[{index}].authority must be planning_only"
            )
        normalized.append(row)

    family_order = [str(row.get("family")) for row in normalized]
    expected_prefix = list(_BLOCKER_FAMILY_ORDER)
    if family_order[: len(expected_prefix)] != expected_prefix:
        raise LandingReadinessBlockerSummaryValidationError(
            "families must start with canonical blocker family order"
        )
    extra = family_order[len(expected_prefix):]
    if any(family != "other" for family in extra) or len(extra) > 1:
        raise LandingReadinessBlockerSummaryValidationError(
            "families may only include one optional other family"
        )
    return normalized


def _validate_blocker_family_name(value: Any, index: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LandingReadinessBlockerSummaryValidationError(
            f"families[{index}].family must be a non-empty string"
        )
    if value not in set(_BLOCKER_FAMILY_ORDER) | {"other"}:
        raise LandingReadinessBlockerSummaryValidationError(
            f"families[{index}].family is not allowed"
        )
    return value


def _expected_clearance_status(
    *,
    family: str,
    blocker_count: int,
    non_present_evidence_ids: list[str],
) -> str:
    if blocker_count > 0:
        return "blocked"
    if family == "change_batch":
        return "human_review_required"
    if non_present_evidence_ids:
        return "evidence_gap"
    return "evidence_present"


def _validate_blocker_summary_counts(
    *,
    total_blockers: int,
    family_counts: Mapping[str, Any],
    evidence_status_counts: Mapping[str, Any],
    families: list[Mapping[str, Any]],
) -> None:
    missing = sorted(
        family for family in _BLOCKER_FAMILY_ORDER if family not in family_counts
    )
    if missing:
        raise LandingReadinessBlockerSummaryValidationError(
            "family_counts missing fields: " + ", ".join(missing)
        )
    for family in _BLOCKER_FAMILY_ORDER:
        _validate_nonnegative_int_for_blocker_summary(
            family_counts.get(family),
            f"family_counts.{family}",
        )
    for key, value in evidence_status_counts.items():
        if not isinstance(key, str) or not key.strip():
            raise LandingReadinessBlockerSummaryValidationError(
                "evidence_status_counts keys must be non-empty strings"
            )
        _validate_nonnegative_int_for_blocker_summary(
            value,
            f"evidence_status_counts.{key}",
        )

    by_family = {str(row["family"]): row for row in families}
    for family in _BLOCKER_FAMILY_ORDER:
        if family_counts.get(family) != by_family[family]["blocker_count"]:
            raise LandingReadinessBlockerSummaryValidationError(
                f"family_counts.{family} must match family blocker_count"
            )
    family_blocker_total = sum(int(row["blocker_count"]) for row in families)
    if total_blockers != family_blocker_total:
        raise LandingReadinessBlockerSummaryValidationError(
            "total_blockers must match sum of family blocker counts"
        )


def _validate_next_clearance_family(
    value: Any,
    *,
    families: list[Mapping[str, Any]],
) -> None:
    actionable_statuses = {"blocked", "evidence_gap", "human_review_required"}
    actionable = [
        str(row["family"])
        for row in families
        if row.get("clearance_status") in actionable_statuses
    ]
    if value is None:
        if actionable:
            raise LandingReadinessBlockerSummaryValidationError(
                "next_clearance_family must identify the first actionable family"
            )
        return
    if not isinstance(value, str) or not value.strip():
        raise LandingReadinessBlockerSummaryValidationError(
            "next_clearance_family must be a non-empty string or None"
        )
    if value != (actionable[0] if actionable else None):
        raise LandingReadinessBlockerSummaryValidationError(
            "next_clearance_family must identify the first actionable family"
        )


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
