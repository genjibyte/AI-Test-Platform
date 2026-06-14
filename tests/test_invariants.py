"""Invariant descriptor + carry tests (docs/48 S1). S1 declares and carries invariants;
it verifies nothing and changes no verdict. Offline; no model, no PIT.
"""
from app.benchmark.invariants import (
    ANCHORING_SOURCES,
    INVARIANT_KINDS,
    InvariantDescriptor,
    invariant_review_view,
    is_anchoring,
    is_known_kind,
    is_known_source,
    parse_invariants,
)


# --- descriptor + vocab ----------------------------------------------------------

def test_descriptor_defaults_are_unknown_and_non_committal():
    d = InvariantDescriptor(statement="order PAID->SHIPPED allowed once")
    assert d.kind == "unknown" and d.source == "unknown"
    assert d.target_class is None and d.observable is None


def test_is_known_kind_and_source():
    assert is_known_kind("exception") and is_known_kind("STATE_TRANSITION")  # normalized
    assert not is_known_kind("teleport")
    assert is_known_source("manifest") and not is_known_source("oracle")
    assert "exception" in INVARIANT_KINDS


# --- parse_invariants: lenient / non-blocking ------------------------------------

def test_parse_invariants_none_and_non_list():
    assert parse_invariants(None) == []
    assert parse_invariants("not a list") == []
    assert parse_invariants(123) == []


def test_parse_invariants_from_strings_and_dicts():
    out = parse_invariants([
        "coupon below min-spend is rejected",
        {"statement": "expired coupon throws", "kind": "exception",
         "observable": "exception:CouponExpiredException", "source": "manifest"},
    ])
    assert len(out) == 2
    assert out[0].statement == "coupon below min-spend is rejected"
    assert out[1].kind == "exception" and out[1].source == "manifest"


def test_parse_invariants_skips_malformed_and_empty():
    out = parse_invariants(["", "  ", {"kind": ["bad", "type"]}, 42, None])
    assert out == []                       # empties skipped, bad-typed dict skipped, never raises


def test_parse_invariants_passes_through_descriptor_instances():
    d = InvariantDescriptor(statement="x", kind="boundary")
    assert parse_invariants([d]) == [d]


# --- anti-self-certification (docs/48 section 2) ----------------------------------

def test_only_manifest_human_can_anchor():
    assert is_anchoring(InvariantDescriptor(statement="x", source="manifest"))
    assert is_anchoring(InvariantDescriptor(statement="x", source="human"))
    # a model-declared invariant is UNTRUSTED -> cannot anchor / self-certify
    assert not is_anchoring(InvariantDescriptor(statement="x", source="model"))
    assert not is_anchoring(InvariantDescriptor(statement="x", source="unknown"))
    assert set(ANCHORING_SOURCES) == {"manifest", "human"}


# --- advisory view: declared, never verified, never accepts -----------------------

def test_invariant_review_view_is_advisory_and_unverified():
    view = invariant_review_view([
        InvariantDescriptor(statement="a", kind="boundary", source="manifest"),
        InvariantDescriptor(statement="b", source="model"),
    ])
    assert view["count"] == 2
    assert view["auto_accept_blocked"] is True               # declaring never accepts
    assert all(item["verified"] is None for item in view["invariants"])  # S1 does not verify
    assert view["invariants"][0]["anchoring"] is True        # manifest anchors
    assert view["invariants"][1]["anchoring"] is False       # model cannot self-certify


def test_invariant_review_view_empty():
    view = invariant_review_view([])
    assert view["count"] == 0 and view["invariants"] == [] and view["auto_accept_blocked"] is True


# --- carry: case -> result -> ledger (no verdict change) --------------------------

def test_case_tags_carries_invariants():
    from app.benchmark.models import BenchCase
    from app.benchmark.runner import _case_tags

    case = BenchCase(repo_url="u", target_class="C",
                     invariants=[InvariantDescriptor(statement="x", source="manifest")])
    tags = _case_tags(case)
    assert [d.statement for d in tags["invariants"]] == ["x"]


def test_review_summary_attaches_invariant_view_even_without_business_tags():
    from app.benchmark.models import BenchCase
    from app.benchmark.runner import _review_summary_with_rubric

    case = BenchCase(repo_url="u", target_class="C",
                     invariants=[InvariantDescriptor(statement="x", source="manifest")])
    out = _review_summary_with_rubric({"k": 1}, case)
    assert "invariant_review" in out and out["invariant_review"]["count"] == 1
    assert "business_rubric" not in out                      # no business tags declared
    # no tags and no invariants -> unchanged passthrough
    bare = BenchCase(repo_url="u", target_class="C")
    assert _review_summary_with_rubric({"k": 1}, bare) == {"k": 1}


def test_invariants_carry_to_ledger_as_dicts():
    from app.benchmark.models import BenchCaseResult
    from app.ledger.ingest import record_from_bench_case
    from app.ledger.models import Provenance

    prov = Provenance(author_type="platform_generator", author_id="m")
    res = BenchCaseResult(
        name="c", repo_url="u", target_class="C", conclusion="NEED_HUMAN_REVIEW",
        invariants=[InvariantDescriptor(statement="expired coupon throws", kind="exception",
                                        source="manifest")],
    )
    rec = record_from_bench_case(res, prov)
    assert rec.invariants == [
        {"id": None, "statement": "expired coupon throws", "kind": "exception",
         "target_class": None, "target_method": None, "target_lines": None,
         "observable": None, "source": "manifest"},
    ]
    # carrying an invariant never flips the conclusion (declared intent only)
    assert res.conclusion == "NEED_HUMAN_REVIEW"
    bare = BenchCaseResult(name="c", repo_url="u", target_class="C")
    assert record_from_bench_case(bare, prov).invariants == []
