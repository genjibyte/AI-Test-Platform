"""Business-invariant tag tests (docs/45 S1). Offline: no model, no pipeline.

Tags are advisory metadata -- declared intent, NOT verified value -- carried read-only
case -> result -> record. They never change judging (conclusion stays NEED_HUMAN_REVIEW).
"""
from app.benchmark.business_tags import (
    BUSINESS_DOMAINS,
    BUSINESS_PATTERNS,
    RISK_LEVELS,
    is_known_domain,
    is_known_pattern,
    is_known_risk,
    normalize_tag,
)
from app.benchmark.models import BenchCase, BenchCaseResult, load_spec
from app.benchmark.runner import run_benchmark
from app.ledger.ingest import record_from_bench_case
from app.ledger.models import Provenance


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
