"""Test-Level Router tests (docs/55 S4A/S5A).

Pure, offline, report-only. The router maps Asset Gate facts to reviewer context; it never
launches an executor or changes a verdict.
"""
import ast
from pathlib import Path

import pytest

from app.benchmark.models import BenchCaseResult, BenchReport, aggregate
from app.benchmark.report_md import render_markdown
from app.ledger.analytics import badcase_signature
from app.ledger.ingest import record_from_bench_case
from app.ledger.models import JudgedRecord, Provenance
import app.quality.test_level_router as router_module
from app.quality.test_level_router import route_test_level


@pytest.mark.parametrize(
    ("asset_level", "support", "owner_gate", "reason_code"),
    [
        ("unit", "supported", False, "asset_level_unit"),
        ("api", "future_gated", True, "asset_level_api_future_gated"),
        ("integration", "future_gated", True, "asset_level_integration_future_gated"),
        (
            "manual_oracle_first",
            "manual_review_required",
            True,
            "asset_level_manual_oracle_first",
        ),
    ],
)
def test_route_maps_asset_level_to_kernel_support(asset_level, support, owner_gate, reason_code):
    routed = route_test_level(
        asset_sufficiency={"test_level_recommendation": asset_level},
    )

    assert routed["recommended_level"] == asset_level
    assert routed["current_kernel_support"] == support
    assert routed["owner_gate_required"] is owner_gate
    assert routed["report_only"] is True
    assert routed["advisory"] is True
    assert routed["reason_codes"] == [reason_code]
    assert routed["evidence"] == [{
        "source": "asset_sufficiency",
        "field": "test_level_recommendation",
        "value": asset_level,
    }]
    assert routed["note"] == "test-level routing is advisory and launches no executor"


@pytest.mark.parametrize("asset_sufficiency", [None, {}, {"test_level_recommendation": "bogus"}])
def test_missing_or_unknown_asset_level_is_owner_gated_unknown(asset_sufficiency):
    routed = route_test_level(asset_sufficiency=asset_sufficiency)

    assert routed["recommended_level"] == "unknown"
    assert routed["current_kernel_support"] == "unknown"
    assert routed["owner_gate_required"] is True
    assert routed["reason_codes"] == ["asset_level_unknown"]
    assert routed["evidence"][0]["value"] == "unknown"


def test_provenance_is_context_not_proof_and_does_not_change_route():
    base = route_test_level(
        asset_sufficiency={"test_level_recommendation": "api"},
    )
    with_provenance = route_test_level(
        asset_sufficiency={"test_level_recommendation": "api"},
        run_kind="external",
        producer_id="external-codex",
    )

    assert with_provenance["recommended_level"] == base["recommended_level"] == "api"
    assert with_provenance["current_kernel_support"] == base["current_kernel_support"]
    assert with_provenance["owner_gate_required"] == base["owner_gate_required"]
    assert "provenance_is_context_not_proof" in with_provenance["reason_codes"]
    assert with_provenance["evidence"][1] == {
        "source": "provenance",
        "run_kind": "external",
        "producer_id_present": True,
    }
    assert "external-codex" not in str(with_provenance)


def test_s5a_router_module_has_no_integration_imports():
    """Closeout audit: the router remains one pure helper, not a hidden executor."""
    tree = ast.parse(Path(router_module.__file__).read_text(encoding="utf-8"))
    imported_roots = {
        node.module.split(".", 1)[0]
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    imported_roots.update(
        alias.name.split(".", 1)[0]
        for node in tree.body
        if isinstance(node, ast.Import)
        for alias in node.names
    )

    assert imported_roots <= {"__future__", "typing"}


def test_s5a_router_stays_report_only_not_benchmark_or_ledger_carry():
    review_summary = {
        "asset_sufficiency": {
            "test_level_recommendation": "api",
            "missing_assets": ["api_schema"],
            "risk_notes": [],
        },
        "test_level_router": {
            "recommended_level": "api",
            "current_kernel_support": "future_gated",
            "owner_gate_required": True,
            "report_only": True,
            "advisory": True,
            "reason_codes": ["asset_level_api_future_gated"],
        },
    }
    case = BenchCaseResult(
        name="api-looking-unit-candidate",
        repo_url="https://example.test/repo.git",
        target_class="com.example.OwnerApiClient",
        target_method="ownerName",
        repo_judged=True,
        generation_status="GEN_DONE",
        gen_outcome="TEST_FAILURE",
        compiled=True,
        executed=True,
        passed=False,
        failure_type="TEST_FAILURE",
        run_kind="real",
        conclusion="NEED_HUMAN_REVIEW",
        review_summary=review_summary,
        asset_test_level_recommendation="api",
        asset_missing_count=1,
        asset_partial_count=0,
    )
    before_keys = set(aggregate([case]).keys())

    md = render_markdown(BenchReport(cases=[case], aggregate=aggregate([case])))
    record = record_from_bench_case(
        case,
        Provenance(author_type="platform_generator", author_id="fake-1"),
    )

    assert "test_level_router" not in aggregate([case])
    assert set(aggregate([case]).keys()) == before_keys
    assert "test_level_router" not in md
    assert "future_gated" not in md
    assert "test_level_router" not in JudgedRecord.model_fields
    assert "router_recommended_level" not in JudgedRecord.model_fields
    assert "test_level_router" not in record.model_dump()
    assert record.asset_test_level_recommendation == "api"
    assert badcase_signature(record) == (
        "TEST_FAILURE@com.example.OwnerApiClient#ownerName"
    )
