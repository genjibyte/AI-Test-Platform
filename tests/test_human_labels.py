"""Human review/RCA label contract tests (docs/57). Pure; no persistence."""
from __future__ import annotations

from copy import deepcopy

import pytest

from app.review.human_labels import (
    HumanLabelValidationError,
    SCHEMA_VERSION,
    label_metric_projection,
    validate_human_review_label,
)


def _valid_label(**overrides):
    label = {
        "schema_version": SCHEMA_VERSION,
        "record_ref": "bench:case-1",
        "candidate_ref": "job:1",
        "reviewer_ref": "reviewer:local",
        "review_started_at": "2026-07-15T10:00:00Z",
        "review_completed_at": "2026-07-15T10:07:00Z",
        "disposition": "kept_with_edits",
        "disposition_reason": "kept after assertion and fixture edits",
        "manual_revision_count": 2,
        "manual_revision_kinds": ["assertion", "fixture"],
        "root_cause": {
            "family": "oracle",
            "code": "oracle_weak_or_missing",
            "confidence": "human_confirmed",
            "recorded_at": "2026-07-15T10:05:00Z",
            "evidence_refs": ["report.quality.blockers:no_assertions"],
            "note": "candidate was green but did not assert the behavior",
        },
        "fix_note": {
            "action": "rewrite_assertion_or_expected_value",
            "changed_test": True,
            "changed_production": False,
        },
        "misjudgment": {
            "kind": "none",
            "misled_human": False,
        },
    }
    label.update(overrides)
    return label


def test_valid_label_is_normalized_without_mutating_input_and_projects_metrics():
    label = _valid_label()
    before = deepcopy(label)

    normalized = validate_human_review_label(label)
    projection = label_metric_projection(label)

    assert label == before
    assert normalized["schema_version"] == SCHEMA_VERSION
    assert projection == {
        "schema_version": "human_review_metric_projection.v1",
        "source_schema_version": SCHEMA_VERSION,
        "human_reviewed": True,
        "disposition": "kept_with_edits",
        "usable_test": True,
        "manual_revision_count": 2,
        "manual_revision_kinds": ["assertion", "fixture"],
        "human_handling_time_seconds": 420,
        "root_cause_family": "oracle",
        "root_cause_code": "oracle_weak_or_missing",
        "root_cause_confidence": "human_confirmed",
        "root_cause_recorded": True,
        "defect_discovery_label": False,
        "fix_action": "rewrite_assertion_or_expected_value",
        "changed_test": True,
        "changed_production": False,
        "misjudgment_kind": "none",
        "misjudgment_signal": None,
        "misled_human": False,
        "advisory_only": True,
        "conclusion": "NEED_HUMAN_REVIEW",
        "trusted": False,
    }


def test_missing_review_fields_mean_not_reviewed_yet():
    projection = label_metric_projection({"record_ref": "bench:case-2"})

    assert projection["human_reviewed"] is False
    assert projection["disposition"] is None
    assert projection["usable_test"] is None
    assert projection["manual_revision_count"] == 0
    assert projection["conclusion"] == "NEED_HUMAN_REVIEW"
    assert projection["trusted"] is False


@pytest.mark.parametrize("field", ["trusted", "auto_accept", "conclusion"])
def test_authority_fields_are_rejected(field):
    label = _valid_label(**{field: True})

    with pytest.raises(HumanLabelValidationError, match="authority field"):
        validate_human_review_label(label)


def test_nested_authority_fields_are_rejected_too():
    label = _valid_label(root_cause={
        "family": "platform",
        "code": "platform_judge_bug",
        "confidence": "human_confirmed",
        "trusted": True,
    })

    with pytest.raises(HumanLabelValidationError, match="root_cause.trusted"):
        validate_human_review_label(label)


def test_kept_with_edits_requires_positive_revision_count_and_kind():
    with pytest.raises(HumanLabelValidationError, match="manual_revision_count > 0"):
        validate_human_review_label(
            _valid_label(manual_revision_count=0, manual_revision_kinds=["assertion"])
        )

    with pytest.raises(HumanLabelValidationError, match="manual_revision_kind"):
        validate_human_review_label(
            _valid_label(manual_revision_count=1, manual_revision_kinds=["magic"])
        )

    with pytest.raises(HumanLabelValidationError, match="manual_revision_kinds"):
        validate_human_review_label(
            _valid_label(manual_revision_count=1, manual_revision_kinds=[])
        )


def test_product_bug_confirmed_requires_confirmation_and_evidence_refs():
    base_root = {
        "family": "product",
        "code": "product_bug_confirmed",
        "confidence": "uncertain",
        "evidence_refs": ["verifier:defects4j-case-1"],
    }
    with pytest.raises(HumanLabelValidationError, match="human/verifier confirmation"):
        validate_human_review_label(_valid_label(root_cause=base_root))

    missing_evidence = dict(base_root, confidence="human_confirmed", evidence_refs=[])
    with pytest.raises(HumanLabelValidationError, match="requires evidence_refs"):
        validate_human_review_label(_valid_label(root_cause=missing_evidence))

    valid_product_bug = dict(base_root, confidence="verifier_confirmed")
    projection = label_metric_projection(_valid_label(root_cause=valid_product_bug))

    assert projection["root_cause_code"] == "product_bug_confirmed"
    assert projection["defect_discovery_label"] is True


def test_root_cause_code_must_match_family():
    label = _valid_label(root_cause={
        "family": "mock",
        "code": "oracle_weak_or_missing",
        "confidence": "human_confirmed",
    })

    with pytest.raises(HumanLabelValidationError, match="root_cause.code"):
        validate_human_review_label(label)


def test_non_none_misjudgment_requires_signal_and_human_verdict():
    label = _valid_label(misjudgment={
        "kind": "false_positive",
        "human_verdict": "quality gate warning was not relevant",
        "misled_human": False,
    })
    with pytest.raises(HumanLabelValidationError, match="platform_signal"):
        validate_human_review_label(label)

    label = _valid_label(misjudgment={
        "kind": "severity_mismatch",
        "platform_signal": "review_digest",
        "misled_human": True,
    })
    with pytest.raises(HumanLabelValidationError, match="human_verdict"):
        validate_human_review_label(label)


def test_review_completed_at_must_not_precede_started_at():
    label = _valid_label(
        review_started_at="2026-07-15T10:07:00Z",
        review_completed_at="2026-07-15T10:00:00Z",
    )

    with pytest.raises(HumanLabelValidationError, match="after review_started_at"):
        validate_human_review_label(label)
