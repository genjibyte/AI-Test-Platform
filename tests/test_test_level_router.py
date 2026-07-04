"""Test-Level Router tests (docs/55 S4A).

Pure, offline, report-only. The router maps Asset Gate facts to reviewer context; it never
launches an executor or changes a verdict.
"""

import pytest

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
