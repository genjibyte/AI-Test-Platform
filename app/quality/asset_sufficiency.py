"""Asset Sufficiency Gate (docs/55) -- ADVISORY.

This module estimates whether the facts already present in a candidate report are enough for a
trustworthy human review, and which test level the reviewer should consider. It also extracts the
tiny S2 ``asset_facts`` block from a bounded ``ContextSnapshot`` while the pipeline has it. Both
paths are deterministic, pure, and intentionally small: no repo reads here, no model calls, no
network, no new dependency, and no verdict changes. A missing/partial asset is a review hint,
never a rejection.
"""
from __future__ import annotations

import re
from typing import Any, Optional

ASSET_STATUSES = ("sufficient", "partial", "missing")
TEST_LEVELS = ("unit", "api", "integration", "manual_oracle_first")

_STATUS_RANK = {"sufficient": 0, "partial": 1, "missing": 2}

_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT = re.compile(r"//[^\n]*")
_STRING = re.compile(r'"(?:\\.|[^"\\])*"')

_DEPENDENCY_RE = re.compile(
    r"\b(?:Repository|Client|JdbcTemplate|RestTemplate|WebClient|KafkaTemplate|"
    r"RedisTemplate|MongoClient|DriverManager|getConnection)\b|@Autowired"
)
_DB_RE = re.compile(
    r"\b(?:Repository|JdbcTemplate|MongoClient|RedisTemplate|DriverManager|getConnection)\b"
)
_API_RE = re.compile(
    r"\b(?:MockMvc|WebTestClient|RestAssured|Controller|Endpoint|Resource|RequestMapping|"
    r"GetMapping|PostMapping|PutMapping|DeleteMapping)\b"
)
_DB_NAME_RE = re.compile(r"(?:Repository|Dao)$")
_API_NAME_RE = re.compile(r"(?:Controller|Endpoint|Resource)$")
_MOCK_RE = re.compile(r"\b(?:mock|spy|when|given|verify|Mockito)\s*\(|@(?:Mock|MockBean|Spy)")

_ARTIFACT_CATEGORY_HINTS = {
    "api": (
        "spring-web", "spring-webmvc", "spring-boot-starter-web",
        "rest-assured",
    ),
    "db": (
        "spring-jdbc", "spring-data", "jdbc", "mysql", "postgresql",
        "mongo", "mongodb",
    ),
    "messaging": ("kafka", "redis", "amqp", "rabbit"),
}


def _strip(source: str) -> str:
    s = _BLOCK_COMMENT.sub(" ", source or "")
    s = _LINE_COMMENT.sub(" ", s)
    return _STRING.sub('""', s)


def _issue_codes(quality_gate: Optional[dict]) -> set[str]:
    q = quality_gate or {}
    codes = {i.get("code") for i in (q.get("blocking_issues") or [])}
    codes |= {i.get("code") for i in (q.get("warnings") or [])}
    return {c for c in codes if c}


def _set_asset(
    out: dict,
    asset: str,
    status: str,
    reason: str,
    *,
    evidence: Optional[str] = None,
) -> None:
    """Raise an asset to the worst observed status and record the reason."""
    current = out.get(asset, "sufficient")
    if _STATUS_RANK[status] > _STATUS_RANK.get(current, 0):
        out[asset] = status
    item = {"asset": asset, "status": status, "reason": reason}
    if evidence:
        item["evidence"] = evidence[:240]
    out["evidence"].append(item)
    if status == "missing":
        out["missing_assets"].append(item)
    elif status == "partial":
        out["risk_notes"].append(item)


def _set_level(out: dict, level: str, reason: str) -> None:
    current = out.get("test_level_recommendation", "unit")
    order = {name: i for i, name in enumerate(TEST_LEVELS)}
    if order[level] > order.get(current, 0):
        out["test_level_recommendation"] = level
    out["evidence"].append({
        "asset": "test_level_recommendation",
        "status": out["test_level_recommendation"],
        "reason": reason,
    })


def _has_behavior_sources(grounding: Optional[dict]) -> bool:
    return bool((grounding or {}).get("behavior_sources"))


def _simple_class(target_class: Optional[str]) -> str:
    return (target_class or "").rsplit(".", 1)[-1]


def _list_len(value: Any) -> int:
    try:
        return len(value or [])
    except TypeError:
        return 0


def asset_facts_from_snapshot(snapshot: Any) -> dict:
    """Extract the tiny persisted asset-facts block from a bounded ContextSnapshot.

    This intentionally stores counts and dependency artifact ids only. It never persists source
    excerpts or the full snapshot (docs/55 S2).
    """
    neighbor = getattr(snapshot, "neighbor_test", None)
    deps = getattr(snapshot, "maven_dependencies", None) or []
    structure = getattr(snapshot, "class_structure", None)
    constraints = getattr(snapshot, "build_constraints", None)
    dep_artifacts = sorted({
        str(getattr(dep, "artifact_id", "")).strip()
        for dep in deps
        if str(getattr(dep, "artifact_id", "")).strip()
    })
    return {
        "neighbor_test_found": bool(getattr(neighbor, "found", False)),
        "neighbor_test_methods": _list_len(getattr(neighbor, "test_methods", [])),
        "dependency_artifacts": dep_artifacts[:50],
        "build_java_source": getattr(constraints, "java_source", None),
        "target_has_method_source": bool(getattr(snapshot, "target_method_source", None)),
        "target_method_specified": bool(getattr(snapshot, "target_method", None)),
        "target_fields": _list_len(getattr(structure, "fields", [])),
        "target_constructors": _list_len(getattr(structure, "constructors", [])),
        "target_methods": _list_len(getattr(structure, "methods", [])),
    }


def _artifact_categories(asset_facts: dict) -> set[str]:
    artifacts = [str(a).lower() for a in (asset_facts or {}).get("dependency_artifacts") or []]
    categories: set[str] = set()
    for category, hints in _ARTIFACT_CATEGORY_HINTS.items():
        if any(any(hint in artifact for hint in hints) for artifact in artifacts):
            categories.add(category)
    return categories


def estimate_asset_sufficiency(
    *,
    test_source: str,
    target_class: Optional[str],
    target_method: Optional[str],
    quality_gate: Optional[dict],
    oracle_strength: Optional[dict],
    mock_smells: Optional[dict],
    grounding: Optional[dict],
    preflight: Optional[dict],
    coverage_delta: Optional[dict],
    asset_facts: Optional[dict] = None,
) -> dict:
    """Estimate asset sufficiency from report and optional tiny pipeline asset facts.

    The result is a flat dict by design so report JSON stays easy to read. It never raises and
    never decides acceptance; callers should surface it under ``review_summary``.
    """
    code = _strip(test_source or "")
    qcodes = _issue_codes(quality_gate)
    oracle = (oracle_strength or {}).get("oracle_strength")
    mock_counts = (mock_smells or {}).get("counts") or {}
    asset_facts = asset_facts or {}

    out = {
        "code_context": "sufficient",
        "existing_tests": "sufficient",
        "business_oracle": "sufficient",
        "test_data": "sufficient",
        "api_schema": "sufficient",
        "db_schema": "sufficient",
        "external_dependency_mock": "sufficient",
        "test_level_recommendation": "unit",
        "missing_assets": [],
        "risk_notes": [],
        "evidence": [],
        "advisory": True,
        "note": "asset sufficiency is advisory and changes no verdict",
    }

    if asset_facts:
        if asset_facts.get("neighbor_test_found") and asset_facts.get("neighbor_test_methods", 0) > 0:
            out["evidence"].append({
                "asset": "existing_tests",
                "status": "sufficient",
                "reason": "neighbor test methods are present",
                "evidence": str(asset_facts.get("neighbor_test_methods")),
            })
        elif asset_facts.get("neighbor_test_found"):
            _set_asset(
                out,
                "existing_tests",
                "partial",
                "neighbor test file exists but no test methods were detected",
            )
        else:
            _set_asset(
                out,
                "existing_tests",
                "missing",
                "no neighbor test asset found in bounded context",
            )
    else:
        out["existing_tests"] = "partial"
        out["risk_notes"].append({
            "asset": "existing_tests",
            "status": "partial",
            "reason": "report-local S1 does not persist neighbor-test asset facts",
        })

    if asset_facts and target_method and not asset_facts.get("target_has_method_source"):
        _set_asset(
            out,
            "code_context",
            "missing",
            "target method source was not available in bounded context asset facts",
        )

    if not target_class:
        _set_asset(out, "code_context", "partial", "target class is absent from report facts")
    if target_method is None:
        _set_asset(out, "code_context", "partial", "target method not specified; class-level review")

    if (preflight or {}).get("status") == "FAIL":
        blockers = (preflight or {}).get("blocking_issues") or []
        evidence = "; ".join(
            f"{b.get('code')}:{b.get('evidence')}" for b in blockers[:2]
        )
        _set_asset(
            out,
            "code_context",
            "missing",
            "preflight rejected target-class calls; context/signature asset is insufficient",
            evidence=evidence,
        )

    if oracle in {"none", "weak"}:
        _set_asset(
            out,
            "business_oracle",
            "missing",
            f"structural oracle estimate is {oracle}",
        )
    elif oracle == "mixed":
        _set_asset(
            out,
            "business_oracle",
            "partial",
            "structural oracle estimate is mixed",
        )
    elif oracle == "structural_ok" and not _has_behavior_sources(grounding):
        _set_asset(
            out,
            "business_oracle",
            "partial",
            "structural assertions exist but no behavior_sources are grounded",
        )

    if "missing_behavior_sources" in qcodes:
        _set_asset(
            out,
            "business_oracle",
            "partial",
            "quality gate reported missing behavior sources",
        )

    if mock_counts.get("mock_of_target"):
        _set_asset(
            out,
            "business_oracle",
            "missing",
            "candidate mocks the class under test; unit oracle is not trustworthy",
        )
        _set_asset(
            out,
            "code_context",
            "partial",
            "candidate mocks target logic instead of exercising it",
        )

    if mock_counts.get("real_dependency"):
        _set_asset(
            out,
            "external_dependency_mock",
            "missing",
            "candidate uses a real framework/external dependency in a unit test",
        )

    has_dependency = bool(_DEPENDENCY_RE.search(code))
    simple_target = _simple_class(target_class)
    has_db = bool(_DB_RE.search(code) or _DB_NAME_RE.search(simple_target))
    has_api = bool(_API_RE.search(code) or _API_NAME_RE.search(simple_target))
    has_mock = bool(_MOCK_RE.search(code))
    artifact_categories = _artifact_categories(asset_facts)

    if has_dependency and not has_mock:
        _set_asset(
            out,
            "external_dependency_mock",
            "partial",
            "dependency-like collaborators appear without an obvious mock",
            evidence=", ".join(sorted(artifact_categories)) if artifact_categories else None,
        )
        _set_asset(
            out,
            "test_data",
            "partial",
            "dependency-like collaborator may need fixture data",
        )

    if has_db:
        _set_asset(
            out,
            "db_schema",
            "partial",
            "database/repository-style dependency appears; schema asset may be needed",
            evidence=", ".join(sorted(artifact_categories & {"db", "messaging"})) or None,
        )
        _set_level(out, "integration", "database/repository access suggests integration review")

    if has_api:
        _set_asset(
            out,
            "api_schema",
            "partial",
            "controller/API-style surface detected; API schema may be needed",
            evidence=", ".join(sorted(artifact_categories & {"api"})) or None,
        )
        _set_level(out, "api", "controller/API-style surface detected")

    cov = coverage_delta or {}
    if cov.get("target_improved") is False:
        _set_asset(
            out,
            "code_context",
            "partial",
            "target coverage did not improve; candidate may use the wrong entrypoint",
        )

    weak_or_empty = oracle in {"none", "weak"} or qcodes & {
        "no_assertions", "only_weak_assertions", "tautological_assertion",
    }
    if weak_or_empty and not _has_behavior_sources(grounding):
        _set_level(
            out,
            "manual_oracle_first",
            "weak or absent oracle with no grounded behavior source",
        )

    return out
