"""Report-only test-level router (docs/55 S4A).

Pure advisory mapping from Asset Gate's recommendation to current kernel support.
It launches no executor, reads no files, and changes no verdict.
"""
from __future__ import annotations

from typing import Mapping, Optional

_LEVEL_ROUTES = {
    "unit": ("supported", False, "asset_level_unit"),
    "api": ("future_gated", True, "asset_level_api_future_gated"),
    "integration": ("future_gated", True, "asset_level_integration_future_gated"),
    "manual_oracle_first": (
        "manual_review_required",
        True,
        "asset_level_manual_oracle_first",
    ),
    "unknown": ("unknown", True, "asset_level_unknown"),
}


def _recommended_level(asset_sufficiency: Optional[Mapping[str, object]]) -> str:
    if not asset_sufficiency:
        return "unknown"
    value = asset_sufficiency.get("test_level_recommendation")
    if isinstance(value, str) and value in _LEVEL_ROUTES:
        return value
    return "unknown"


def route_test_level(
    *,
    asset_sufficiency: Optional[Mapping[str, object]],
    run_kind: Optional[str] = None,
    producer_id: Optional[str] = None,
) -> dict:
    """Return an advisory report-only route over existing Asset Gate facts.

    Provenance is context only: it never changes the recommended level or support state.
    """
    level = _recommended_level(asset_sufficiency)
    support, owner_gate_required, reason_code = _LEVEL_ROUTES[level]
    reason_codes = [reason_code]
    evidence = [{
        "source": "asset_sufficiency",
        "field": "test_level_recommendation",
        "value": level,
    }]

    if run_kind is not None or producer_id is not None:
        reason_codes.append("provenance_is_context_not_proof")
        evidence.append({
            "source": "provenance",
            "run_kind": run_kind,
            "producer_id_present": bool(producer_id),
        })

    return {
        "recommended_level": level,
        "current_kernel_support": support,
        "owner_gate_required": owner_gate_required,
        "report_only": True,
        "advisory": True,
        "reason_codes": reason_codes,
        "evidence": evidence,
        "note": "test-level routing is advisory and launches no executor",
    }
