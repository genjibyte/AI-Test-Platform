"""Business-invariant tag tests (docs/45 S1). Offline: no model, no pipeline.

Tags are advisory metadata -- declared intent, NOT verified value -- carried read-only
case -> result -> record. They never change judging (conclusion stays NEED_HUMAN_REVIEW).
"""
import uuid

from app.benchmark.business_tags import (
    BUSINESS_DOMAINS,
    BUSINESS_PATTERNS,
    RISK_LEVELS,
    business_review_rubric,
    is_known_domain,
    is_known_pattern,
    is_known_risk,
    normalize_tag,
)
from app.benchmark.models import (
    BenchCase,
    BenchCaseResult,
    business_breakdown,
    load_spec,
)
from app.benchmark.runner import run_benchmark
from app.ledger.analytics import business_summary
from app.ledger.ingest import record_from_bench_case
from app.ledger.models import JudgedRecord, Provenance


def test_vocab_always_allows_other_and_unknown():
    for vocab in (BUSINESS_DOMAINS, BUSINESS_PATTERNS):
        assert "other" in vocab and "unknown" in vocab
    assert "unknown" in RISK_LEVELS


def test_normalize_tag_lowercases_strips_and_empties_to_none():
    assert normalize_tag("  Payments ") == "payments"
    assert normalize_tag("") is None
    assert normalize_tag(None) is None


def test_is_known_is_a_non_blocking_predicate():
    # Known values resolve case-insensitively; unknown values are *allowed*, just not known.
    assert is_known_domain("payments") and is_known_domain("PAYMENTS")
    assert not is_known_domain("teleportation")
    assert is_known_pattern("idempotency") and not is_known_pattern("vibes")
    assert is_known_risk("high") and not is_known_risk("apocalyptic")


def test_manifest_loads_business_tags():
    cases = load_spec({"cases": [{
        "repo_url": "u", "target_class": "C",
        "business_domain": "payments", "business_pattern": "idempotency",
        "expected_invariant": "same idempotency key must not create a duplicate charge",
        "risk_level": "high",
    }, {
        "repo_url": "u2", "target_class": "D",   # untagged case stays None (back-compat)
    }]})
    tagged, bare = cases
    assert tagged.business_domain == "payments" and tagged.business_pattern == "idempotency"
    assert tagged.risk_level == "high" and "idempotency key" in tagged.expected_invariant
    assert bare.business_domain is None and bare.expected_invariant is None


def _result(**kw):
    base = dict(name="c", repo_url="u", target_class="C", gen_outcome="PASS",
                passed=True, conclusion="NEED_HUMAN_REVIEW")
    base.update(kw)
    return BenchCaseResult(**base)


def test_tags_carry_into_ledger_record():
    prov = Provenance(author_type="platform_generator", author_id="m")
    rec = record_from_bench_case(_result(
        business_domain="payments", business_pattern="idempotency",
        expected_invariant="no duplicate charge", risk_level="high"), prov)
    assert rec.business_domain == "payments" and rec.business_pattern == "idempotency"
    assert rec.expected_invariant == "no duplicate charge" and rec.risk_level == "high"
    # absent tags default to None and judging is unchanged (advisory only)
    bare = record_from_bench_case(_result(), prov)
    assert bare.business_domain is None and bare.conclusion == "NEED_HUMAN_REVIEW"


def test_runner_carries_case_tags_even_on_setup_failure(tmp_path, monkeypatch):
    # Tags describe the target, so they must be carried regardless of outcome.
    monkeypatch.setenv("TESTAGENT_LEDGER_DB", str(tmp_path / "ledger.db"))

    def boom(_settings):
        raise ValueError("missing key")

    monkeypatch.setattr("app.benchmark.runner.get_client", boom)
    report = run_benchmark([BenchCase(
        repo_url="https://example.invalid/r.git", target_class="C",
        business_domain="payments", business_pattern="idempotency",
        expected_invariant="no duplicate charge", risk_level="high",
    )], workdir=tmp_path)

    r = report.cases[0]
    assert r.failure_type == "LLM_CONFIG_FAILED"          # the _case_failure path
    assert r.business_domain == "payments" and r.business_pattern == "idempotency"
    assert r.expected_invariant == "no duplicate charge" and r.risk_level == "high"


# --- S2: descriptive group-by (docs/45 S2) ---------------------------------------

def _bcr(**kw):
    base = dict(name="x", repo_url="u", target_class="C", repo_judged=True)
    base.update(kw)
    return BenchCaseResult(**base)


def test_business_breakdown_groups_normalizes_and_composes_with_run_kind():
    cases = [
        _bcr(run_kind="real", business_domain="payments", business_pattern="idempotency"),
        _bcr(run_kind="real", business_domain="Payments", business_pattern="state_transition"),
        _bcr(run_kind="fake", business_domain="payments", business_pattern="idempotency"),
        _bcr(run_kind="real"),  # untagged real -> unknown bucket
    ]
    raw = business_breakdown(cases)
    real = business_breakdown(cases, run_kind="real")
    assert raw["total"] == 4 and raw["by_domain"]["payments"] == 3   # "Payments" normalizes in
    assert real["run_kind_filter"] == "real" and real["total"] == 3  # fake excluded
    assert real["by_domain"] == {"payments": 2, "unknown": 1}
    assert real["by_pattern"] == {"idempotency": 1, "state_transition": 1, "unknown": 1}


def _jr(domain=None, pattern=None, run_kind=None):
    return JudgedRecord(
        record_id=str(uuid.uuid4()), repo_url="u", target_class="C",
        provenance=Provenance(author_type="platform_generator", author_id="m"),
        business_domain=domain, business_pattern=pattern, run_kind=run_kind,
    )


def test_business_summary_groups_ledger_records_and_composes_with_run_kind():
    records = [
        _jr("payments", "idempotency", "real"),
        _jr("payments", "idempotency", "fake"),
        _jr(None, None, "real"),
    ]
    raw = business_summary(records)
    real = business_summary(records, run_kind="real")
    assert raw["records"] == 3 and raw["by_domain"]["payments"] == 2
    assert real["run_kind_filter"] == "real" and real["records"] == 2
    assert real["by_domain"] == {"payments": 1, "unknown": 1}


def test_report_md_renders_business_section():
    from app.benchmark.models import BenchReport, aggregate
    from app.benchmark.report_md import render_markdown
    case = _bcr(run_kind="real", business_domain="payments", business_pattern="idempotency",
                gen_outcome="PASS", passed=True, conclusion="NEED_HUMAN_REVIEW")
    report = BenchReport(cases=[case], aggregate=aggregate([case]))
    md = render_markdown(report)
    assert "Business tags" in md and "by_pattern" in md and "idempotency" in md


# --- S3: advisory human-review rubric (docs/45 S3) -------------------------------

def test_business_review_rubric_is_advisory_and_untrusted():
    r = business_review_rubric(
        business_domain="Payments", business_pattern="idempotency",
        expected_invariant="no duplicate charge", risk_level="HIGH",
        declared_invariant="model says it checks dedup",
    )
    # authoritative (manifest) facts, normalized
    assert r["business_domain"] == "payments" and r["risk_level"] == "high"
    assert r["expected_invariant"] == "no duplicate charge"
    # a model-declared invariant is captured but NEVER trusted (anti-hallucination)
    assert r["declared_invariant"] == "model says it checks dedup"
    assert r["declared_invariant_trusted"] is False
    # the human fills these; the platform never computes them
    assert r["oracle_strength"] is None and r["fake_green_risk"] is None
    assert r["human_review_note"] is None
    # a tag never accepts a candidate
    assert r["auto_accept_blocked"] is True


def test_review_summary_with_rubric_attaches_only_when_tagged():
    from app.benchmark.runner import _review_summary_with_rubric
    tagged = BenchCase(repo_url="u", target_class="C",
                       business_domain="payments", expected_invariant="no dup charge")
    untagged = BenchCase(repo_url="u", target_class="C")
    base = {"invariants": {"auto_accept_blocked": True}}
    # untagged -> review summary returned unchanged (no noise added)
    assert _review_summary_with_rubric(base, untagged) is base
    # tagged -> business_rubric attached; original keys preserved; base not mutated
    out = _review_summary_with_rubric(base, tagged)
    assert "business_rubric" in out and out["invariants"] == {"auto_accept_blocked": True}
    assert out["business_rubric"]["expected_invariant"] == "no dup charge"
    assert "business_rubric" not in base
    # None review summary + tagged -> a fresh dict with just the rubric
    only = _review_summary_with_rubric(None, tagged)
    assert set(only.keys()) == {"business_rubric"}
