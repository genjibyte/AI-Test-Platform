"""Golden Set manifest governance presentation tests (S5B2)."""
from __future__ import annotations

import pytest

from app.benchmark.manifest_governance import (
    GOLDEN_MANIFEST_SEED_SCHEMA_VERSION,
    GoldenManifestSeedValidationError,
)
from app.benchmark.manifest_governance_report import (
    render_golden_manifest_governance_markdown,
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


def test_render_golden_manifest_governance_markdown_omits_empty_plans():
    assert render_golden_manifest_governance_markdown([]) == ""


def test_render_golden_manifest_governance_markdown_is_presentation_only():
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

    md = render_golden_manifest_governance_markdown([
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
    ])

    assert "## Golden Set manifest governance - METADATA PLAN" in md
    assert "total_records: 2" in md
    assert "metadata_only_records: ['defects4j-chart-1', 'openapi-schema-seed']" in md
    assert "small_seed_policy_ok_records: ['defects4j-chart-1']" in md
    assert "large_seed_request_records: ['openapi-schema-seed']" in md
    assert "runtime_risk_records: ['openapi-schema-seed']" in md
    assert "benchmark_headline_allowed_records=[]" in md
    assert "verdict_authority_records=[]" in md
    assert "dataset slice, execution, headline metric, or verdict authority" in md
    assert "| openapi-schema-seed | api_schema_candidate | 8 |" in md
    assert "network_required, docker_required, model_or_api_key_required" in md
    assert "requires_network, requires_docker, requires_model_or_api_key" in md
    assert "accept_rate" not in md
    assert "usable_test" not in md
    assert "trusted=True" not in md
    assert set(aggregate(cases).keys()) == before_keys
    assert "benchmark_headline_allowed_records" not in aggregate(cases)


def test_render_golden_manifest_governance_markdown_reuses_seed_validation():
    with pytest.raises(GoldenManifestSeedValidationError, match="must not contain"):
        render_golden_manifest_governance_markdown([
            _seed(headline_metric={"pass_rate": 1.0}),
        ])


def test_render_golden_manifest_governance_markdown_escapes_table_cells():
    md = render_golden_manifest_governance_markdown([
        _seed(
            asset_id="seed|one",
            project_artifact="benchmarks/manifest.golden.draft.json",
        ),
    ])

    assert "| seed/one | junit_unit_candidate | 3 |" in md
