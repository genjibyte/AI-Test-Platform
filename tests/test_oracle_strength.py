"""Oracle-strength estimate tests (docs/46 S1). Offline.

The estimate is an ADVISORY, STRUCTURAL roll-up of quality-gate facts -- never semantic
proof, never a verdict. It reuses the gate's issue codes/metrics (no new parser).
"""
import uuid

from app.benchmark.models import (
    BenchCaseResult,
    BenchReport,
    aggregate,
    oracle_strength_breakdown,
)
from app.benchmark.report_md import render_markdown
from app.ledger.analytics import oracle_strength_summary
from app.ledger.ingest import record_from_bench_case
from app.ledger.models import JudgedRecord, Provenance
from app.quality.oracle_strength import ORACLE_STRENGTHS, estimate_oracle_strength
from app.quality.test_quality_gate import evaluate_test_quality


def _gate(blocking=(), warnings=(), checked=True, metrics=None):
    return {
        "checked": checked,
        "status": "FAIL" if blocking else ("REVIEW" if warnings else "PASS"),
        "blocking_issues": [{"code": c} for c in blocking],
        "warnings": [{"code": c} for c in warnings],
        "metrics": metrics or {},
    }


def test_levels_from_issue_codes():
    assert estimate_oracle_strength(_gate(blocking=["no_assertions"]))["oracle_strength"] == "none"
    assert estimate_oracle_strength(_gate(blocking=["no_test_methods"]))["oracle_strength"] == "none"
    assert estimate_oracle_strength(_gate(blocking=["only_weak_assertions"]))["oracle_strength"] == "weak"
    assert estimate_oracle_strength(_gate(blocking=["tautological_assertion"]))["oracle_strength"] == "weak"
    assert estimate_oracle_strength(_gate(warnings=["weak_assertion_heavy"]))["oracle_strength"] == "mixed"
    assert estimate_oracle_strength(_gate())["oracle_strength"] == "structural_ok"


def test_unchecked_or_empty_is_unknown():
    assert estimate_oracle_strength(None)["oracle_strength"] == "unknown"
    assert estimate_oracle_strength({"checked": False})["oracle_strength"] == "unknown"


def test_estimate_is_advisory_and_never_semantic():
    est = estimate_oracle_strength(_gate(
        warnings=["missing_behavior_sources"],
        metrics={"assertions": 3, "weak_assertions": 0, "tautological_assertions": 0},
    ))
    assert est["oracle_strength"] == "structural_ok"        # caveat does not lower the level
    assert "missing_behavior_sources" in est["reasons"]     # but is carried for the human
    assert est["semantic_strength"] == "human_review"       # never auto-decided
    assert est["advisory"] is True
    assert est["metrics"]["assertions"] == 3
    assert est["oracle_strength"] in ORACLE_STRENGTHS


def test_none_beats_weak_beats_mixed_precedence():
    # if several signals co-occur, the worst (most cautious) level wins
    est = estimate_oracle_strength(_gate(
        blocking=["no_assertions", "only_weak_assertions"], warnings=["weak_assertion_heavy"]))
    assert est["oracle_strength"] == "none"


def test_estimate_over_real_gate_structural_ok():
    src = (
        "import org.junit.jupiter.api.Test;\n"
        "import static org.junit.jupiter.api.Assertions.*;\n"
        "class CalcTest {\n"
        "  @Test void adds() { assertEquals(2, new Calc().add(1, 1)); }\n"
        "}\n"
    )
    gate = evaluate_test_quality(src, execution={"gen_outcome": "PASS"}).model_dump()
    est = estimate_oracle_strength(gate)
    assert est["oracle_strength"] == "structural_ok"        # a real assertEquals
    assert est["semantic_strength"] == "human_review"


def test_estimate_over_real_gate_weak_when_only_assert_not_null():
    src = (
        "import org.junit.jupiter.api.Test;\n"
        "import static org.junit.jupiter.api.Assertions.*;\n"
        "class CalcTest {\n"
        "  @Test void runs() { assertNotNull(new Calc()); }\n"
        "}\n"
    )
    gate = evaluate_test_quality(src, execution={"gen_outcome": "PASS"}).model_dump()
    # assertNotNull only -> gate flags only_weak_assertions -> estimate "weak"
    assert estimate_oracle_strength(gate)["oracle_strength"] == "weak"


# --- S2: carry + descriptive group-by (docs/46 S2) -------------------------------

def _bcr(**kw):
    base = dict(name="x", repo_url="u", target_class="C", repo_judged=True)
    base.update(kw)
    return BenchCaseResult(**base)


def test_oracle_strength_breakdown_composes_with_run_kind():
    cases = [
        _bcr(run_kind="real", oracle_strength="structural_ok"),
        _bcr(run_kind="real", oracle_strength="weak"),
        _bcr(run_kind="fake", oracle_strength="structural_ok"),
        _bcr(run_kind="real"),  # un-analyzed real -> unknown bucket
    ]
    raw = oracle_strength_breakdown(cases)
    real = oracle_strength_breakdown(cases, run_kind="real")
    assert raw["total"] == 4 and raw["by_oracle_strength"]["structural_ok"] == 2
    assert real["run_kind_filter"] == "real" and real["total"] == 3   # fake excluded
    assert real["by_oracle_strength"] == {"structural_ok": 1, "weak": 1, "unknown": 1}


def test_oracle_strength_carries_into_ledger_record():
    prov = Provenance(author_type="platform_generator", author_id="m")
    rec = record_from_bench_case(
        _bcr(oracle_strength="structural_ok", conclusion="NEED_HUMAN_REVIEW"), prov)
    assert rec.oracle_strength == "structural_ok"
    bare = record_from_bench_case(_bcr(conclusion="NEED_HUMAN_REVIEW"), prov)
    assert bare.oracle_strength is None


def _jr(oracle=None, run_kind=None):
    return JudgedRecord(
        record_id=str(uuid.uuid4()), repo_url="u", target_class="C",
        provenance=Provenance(author_type="platform_generator", author_id="m"),
        oracle_strength=oracle, run_kind=run_kind,
    )


def test_oracle_strength_summary_composes_with_run_kind():
    records = [_jr("structural_ok", "real"), _jr("weak", "fake"), _jr(None, "real")]
    raw = oracle_strength_summary(records)
    real = oracle_strength_summary(records, run_kind="real")
    assert raw["records"] == 3 and raw["by_oracle_strength"]["structural_ok"] == 1
    assert real["records"] == 2 and real["by_oracle_strength"] == {"structural_ok": 1, "unknown": 1}


def test_report_md_renders_oracle_section():
    case = _bcr(run_kind="real", oracle_strength="structural_ok",
                gen_outcome="PASS", passed=True, conclusion="NEED_HUMAN_REVIEW")
    report = BenchReport(cases=[case], aggregate=aggregate([case]))
    md = render_markdown(report)
    assert "Oracle strength" in md and "by_oracle_strength" in md and "structural_ok" in md
