"""Golden Set manifest governance tests (S5B)."""
from __future__ import annotations

import pytest

from app.benchmark.manifest_governance import (
    GOLDEN_DEFECT_DENOMINATOR_READINESS_VERSION,
    GOLDEN_MANIFEST_GOVERNANCE_PLAN_VERSION,
    GOLDEN_MANIFEST_SEED_SCHEMA_VERSION,
    GoldenManifestSeedValidationError,
    golden_defect_denominator_readiness,
    golden_manifest_governance_plan,
    validate_golden_manifest_seed,
)
from app.benchmark.models import BenchCaseResult, aggregate


def _seed(**overrides):
    seed = {
        "schema_version": GOLDEN_MANIFEST_SEED_SCHEMA_VERSION,
        "asset_id": "defects4j-chart-1",
        "intake_shape": "manifest_seed",
        "project_artifact": "benchmarks/manifest.golden.draft.json",
        "source_url": "https://github.com/rjust/defects4j",
        "pinned_version_or_commit": "v3.0.1",
        "license_spdx": "MIT",
        "license_verified_at": "2026-07-21",
        "runtime_language": "Java/Perl",
        "task_count_requested": 3,
        "task_ids": ["Chart-1"],
        "candidate_kind": "junit_unit_candidate",
        "expected_evidence": [
            "pinned external task id",
            "expected compile/execute evidence contract",
        ],
        "requires_network": False,
        "requires_docker": False,
        "requires_model_or_api_key": False,
        "red_lines": [
            "no bulk import",
            "no external execution without owner gate",
            "no headline metric",
        ],
        "next_action": "record metadata only",
    }
    seed.update(overrides)
    return seed


def test_valid_golden_manifest_seed_is_metadata_only_without_authority():
    normalized = validate_golden_manifest_seed(_seed())

    assert normalized["schema_version"] == GOLDEN_MANIFEST_SEED_SCHEMA_VERSION
    assert normalized["asset_id"] == "defects4j-chart-1"
    assert normalized["intake_shape"] == "manifest_seed"
    assert normalized["phase_policy"]["current_status"] == "design_allowed_metadata_only"
    assert normalized["metadata_only"] is True
    assert normalized["golden_manifest_draft_allowed_now"] is True
    assert normalized["small_seed_policy_ok"] is True
    assert normalized["future_owner_gate_reasons"] == ["dataset_slice_materialization"]
    assert normalized["runtime_actions_allowed_now"] is False
    assert normalized["download_allowed_now"] is False
    assert normalized["install_allowed_now"] is False
    assert normalized["benchmark_headline_allowed_now"] is False
    assert normalized["verdict_authority"] is False


def test_future_candidate_seed_stays_metadata_only_and_owner_gated():
    normalized = validate_golden_manifest_seed(_seed(
        asset_id="schemathesis-openapi-seed",
        source_url="https://github.com/schemathesis/schemathesis",
        candidate_kind="api_schema_candidate",
        task_count_requested=8,
        task_ids=["schema-a", "schema-b"],
        requires_network=True,
        requires_docker=True,
        requires_model_or_api_key=True,
        runtime_language="Python",
    ))

    assert normalized["candidate_kind"] == "api_schema_candidate"
    assert normalized["small_seed_policy_ok"] is False
    assert normalized["future_owner_gate_reasons"] == [
        "dataset_slice_materialization",
        "task_count_exceeds_small_seed_limit",
        "network_required",
        "docker_required",
        "model_or_api_key_required",
    ]
    assert normalized["runtime_actions_allowed_now"] is False
    assert normalized["download_allowed_now"] is False
    assert normalized["benchmark_headline_allowed_now"] is False


def test_registry_entry_is_allowed_as_a_metadata_holding_artifact():
    normalized = validate_golden_manifest_seed(_seed(
        project_artifact="docs/knowledge/EXTERNAL_PROJECT_AND_BENCHMARK_REGISTRY.md",
    ))

    assert normalized["project_artifact"] == (
        "docs/knowledge/EXTERNAL_PROJECT_AND_BENCHMARK_REGISTRY.md"
    )
    assert normalized["golden_manifest_draft_allowed_now"] is True


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("asset_id", " "),
        ("source_url", " "),
        ("pinned_version_or_commit", " "),
        ("license_spdx", " "),
        ("candidate_kind", " "),
        ("next_action", " "),
    ],
)
def test_seed_requires_non_empty_strings(field, value):
    with pytest.raises(GoldenManifestSeedValidationError, match=field):
        validate_golden_manifest_seed(_seed(**{field: value}))


@pytest.mark.parametrize(
    "field",
    ["requires_network", "requires_docker", "requires_model_or_api_key"],
)
def test_seed_requires_boolean_risk_flags(field):
    with pytest.raises(GoldenManifestSeedValidationError, match=field):
        validate_golden_manifest_seed(_seed(**{field: "false"}))


def test_seed_rejects_wrong_intake_shape_and_unsupported_candidate_kind():
    with pytest.raises(GoldenManifestSeedValidationError, match="intake_shape"):
        validate_golden_manifest_seed(_seed(intake_shape="dataset_slice"))

    with pytest.raises(GoldenManifestSeedValidationError, match="candidate_kind"):
        validate_golden_manifest_seed(_seed(candidate_kind="ui_automation_candidate"))


def test_seed_rejects_artifact_drift_and_secret_bearing_urls():
    with pytest.raises(GoldenManifestSeedValidationError, match="project_artifact"):
        validate_golden_manifest_seed(_seed(
            project_artifact="app/benchmark/runner.py",
        ))

    with pytest.raises(GoldenManifestSeedValidationError, match="source_url"):
        validate_golden_manifest_seed(_seed(
            source_url="https://example.test/repo?token=secret",
        ))

    with pytest.raises(GoldenManifestSeedValidationError, match="http"):
        validate_golden_manifest_seed(_seed(source_url="file:///tmp/repo"))


@pytest.mark.parametrize(
    ("field", "value", "pattern"),
    [
        ("task_count_requested", 0, "> 0"),
        ("task_count_requested", True, "integer"),
        ("expected_evidence", [], "expected_evidence"),
        ("red_lines", [], "red_lines"),
        ("license_verified_at", "2026/07/21", "license_verified_at"),
    ],
)
def test_seed_rejects_invalid_counts_lists_and_dates(field, value, pattern):
    with pytest.raises(GoldenManifestSeedValidationError, match=pattern):
        validate_golden_manifest_seed(_seed(**{field: value}))


def test_seed_rejects_task_ids_beyond_requested_count():
    with pytest.raises(GoldenManifestSeedValidationError, match="task_ids"):
        validate_golden_manifest_seed(_seed(
            task_count_requested=1,
            task_ids=["Chart-1", "Math-2"],
        ))


@pytest.mark.parametrize(
    "unsafe",
    [
        {"cases": [{"id": "Chart-1"}]},
        {"trusted": True},
        {"headline_metric": {"pass_rate": 1.0}},
        {"notes": {"token": "do-not-store"}},
    ],
)
def test_seed_rejects_dataset_content_authority_metrics_or_secrets(unsafe):
    with pytest.raises(GoldenManifestSeedValidationError, match="must not contain"):
        validate_golden_manifest_seed(_seed(**unsafe))


def test_seed_rejects_unknown_fields():
    with pytest.raises(GoldenManifestSeedValidationError, match="unknown fields"):
        validate_golden_manifest_seed(_seed(download_command="curl example"))


def test_golden_manifest_plan_empty_is_safe():
    plan = golden_manifest_governance_plan([])

    assert plan["plan_version"] == GOLDEN_MANIFEST_GOVERNANCE_PLAN_VERSION
    assert plan["total_records"] == 0
    assert plan["metadata_only_records"] == []
    assert plan["runtime_actions_allowed_records"] == []
    assert plan["download_allowed_records"] == []
    assert plan["install_allowed_records"] == []
    assert plan["benchmark_headline_allowed_records"] == []
    assert plan["verdict_authority_records"] == []


def test_golden_manifest_plan_groups_metadata_and_future_gates():
    records = [
        _seed(asset_id="defects4j-chart-1"),
        _seed(
            asset_id="openapi-schema-seed",
            source_url="https://github.com/schemathesis/schemathesis",
            candidate_kind="api_schema_candidate",
            task_count_requested=8,
            requires_network=True,
            requires_docker=True,
            requires_model_or_api_key=True,
        ),
    ]

    plan = golden_manifest_governance_plan(records)

    assert plan["total_records"] == 2
    assert plan["metadata_only_records"] == [
        "defects4j-chart-1",
        "openapi-schema-seed",
    ]
    assert plan["golden_manifest_draft_records"] == [
        "defects4j-chart-1",
        "openapi-schema-seed",
    ]
    assert plan["small_seed_policy_ok_records"] == ["defects4j-chart-1"]
    assert plan["large_seed_request_records"] == ["openapi-schema-seed"]
    assert plan["future_owner_gated_records"] == [
        "defects4j-chart-1",
        "openapi-schema-seed",
    ]
    assert plan["runtime_risk_records"] == ["openapi-schema-seed"]
    assert plan["by_candidate_kind"] == {
        "junit_unit_candidate": 1,
        "api_schema_candidate": 1,
    }
    assert plan["runtime_actions_allowed_records"] == []
    assert plan["download_allowed_records"] == []
    assert plan["install_allowed_records"] == []
    assert plan["benchmark_headline_allowed_records"] == []
    assert plan["verdict_authority_records"] == []
    assert plan["records"][1]["future_owner_gate_reasons"] == [
        "dataset_slice_materialization",
        "task_count_exceeds_small_seed_limit",
        "network_required",
        "docker_required",
        "model_or_api_key_required",
    ]


def test_golden_manifest_plan_rejects_duplicate_asset_ids():
    with pytest.raises(GoldenManifestSeedValidationError, match="duplicate asset_id"):
        golden_manifest_governance_plan([
            _seed(asset_id="same"),
            _seed(asset_id="same", source_url="https://example.test/other"),
        ])


def test_golden_manifest_governance_does_not_mutate_aggregate_headline_shape():
    cases = [
        BenchCaseResult(
            name="case",
            repo_url="https://example.test/repo.git",
            target_class="com.example.Calc",
            repo_judged=True,
            generation_status="GEN_DONE",
            gen_outcome="PASS",
            compiled=True,
            executed=True,
            passed=True,
            conclusion="NEED_HUMAN_REVIEW",
            run_kind="real",
        )
    ]
    before_keys = set(aggregate(cases).keys())

    plan = golden_manifest_governance_plan([_seed()])

    assert set(aggregate(cases).keys()) == before_keys
    assert "benchmark_headline_allowed_records" not in aggregate(cases)
    assert plan["benchmark_headline_allowed_records"] == []


def test_golden_defect_denominator_readiness_is_metadata_only_future_signal():
    records = [
        _seed(
            asset_id="defects4j-chart-1",
            task_count_requested=2,
            task_ids=["Chart-1", "Math-2"],
            expected_evidence=[
                "pinned bug id",
                "bug-revealing verifier metadata",
            ],
        ),
        _seed(
            asset_id="testexplora-generated-test-seed",
            source_url="https://example.test/testexplora",
            task_count_requested=3,
            task_ids=["repo-a"],
            expected_evidence=[
                "generated test benchmark metadata",
                "candidate quality evidence contract",
            ],
            notes="generated-test benchmark seed; comparison only",
        ),
    ]

    summary = golden_defect_denominator_readiness(records)

    assert summary["schema_version"] == GOLDEN_DEFECT_DENOMINATOR_READINESS_VERSION
    assert summary["metadata_only"] is True
    assert summary["total_seed_records"] == 2
    assert summary["defect_denominator_candidate_records"] == ["defects4j-chart-1"]
    assert summary["requested_task_count"] == 2
    assert summary["pinned_task_id_count"] == 2
    assert summary["future_defect_denominator_possible"] is True
    assert summary["defect_denominator_ready_now"] is False
    assert summary["defect_discovery_rate_value"] is None
    assert summary["dataset_materialization_allowed_now"] is False
    assert summary["download_allowed_now"] is False
    assert summary["external_execution_allowed_now"] is False
    assert summary["verifier_execution_allowed_now"] is False
    assert summary["benchmark_headline_allowed_now"] is False
    assert summary["defect_discovery_rate_authority"] is False
    assert summary["verdict_authority"] is False
    assert summary["trusted_authority"] is False
    assert "dataset_slice_materialization_owner_gate_required" in (
        summary["not_ready_reasons"]
    )
    assert summary["records"][0]["defect_denominator_candidate"] is True
    assert summary["records"][1]["defect_denominator_candidate"] is False


def test_golden_defect_denominator_readiness_marks_no_seed_candidate():
    summary = golden_defect_denominator_readiness([
            _seed(
                asset_id="testexplora-generated-test-seed",
                source_url="https://example.test/testexplora",
                expected_evidence=[
                    "generated test benchmark metadata",
                    "quality comparison evidence",
            ],
            notes="support-only benchmark seed",
        )
    ])

    assert summary["defect_denominator_candidate_records"] == []
    assert summary["future_defect_denominator_possible"] is False
    assert summary["defect_denominator_ready_now"] is False
    assert summary["not_ready_reasons"] == ["no_defect_denominator_manifest_seed"]


def test_golden_defect_denominator_readiness_does_not_change_aggregate_shape():
    cases = [
        BenchCaseResult(
            name="case",
            repo_url="https://example.test/repo.git",
            target_class="com.example.Calc",
            conclusion="NEED_HUMAN_REVIEW",
            run_kind="real",
        )
    ]
    before_keys = set(aggregate(cases).keys())

    summary = golden_defect_denominator_readiness([_seed()])

    assert set(aggregate(cases).keys()) == before_keys
    assert summary["benchmark_headline_allowed_now"] is False
