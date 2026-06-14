"""Invariant descriptor + carry tests (docs/48 S1). S1 declares and carries invariants;
it verifies nothing and changes no verdict. Offline; no model, no PIT.
"""
from app.benchmark.invariants import (
    ANCHORING_SOURCES,
    INVARIANT_KINDS,
    INVARIANT_STRENGTHS,
    InvariantDescriptor,
    estimate_invariant_strength,
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


# --- S2: structural verification (estimate_invariant_strength) -------------------

def _anchor(kind="boundary"):
    return InvariantDescriptor(statement="x", kind=kind, source="manifest")


def test_strength_non_anchoring_is_never_blessed():
    # model-declared (non-anchoring) -> unknown regardless of inputs (anti-self-certification)
    d = InvariantDescriptor(statement="x", source="model")
    r = estimate_invariant_strength(d, addressed=True, oracle_strength="structural_ok")
    assert r["invariant_strength"] == "unknown" and r["anchoring"] is False
    assert "non_anchoring_model_declared" in r["reasons"]


def test_strength_unaddressed():
    r = estimate_invariant_strength(_anchor(), addressed=False, oracle_strength="structural_ok")
    assert r["invariant_strength"] == "unaddressed"


def test_strength_addressed_unasserted():
    r = estimate_invariant_strength(_anchor(), addressed=True, oracle_strength="none")
    assert r["invariant_strength"] == "addressed_unasserted" and r["asserted"] is False


def test_strength_asserted_unpinned_is_the_s2_ceiling():
    r = estimate_invariant_strength(_anchor(), addressed=True, oracle_strength="structural_ok")
    assert r["invariant_strength"] == "asserted_unpinned" and r["asserted"] is True
    assert "pinned_needs_mutation" in r["reasons"]


def test_strength_unknown_when_coverage_unavailable():
    # coverage off (addressed=None) -> unknown, but the asserted fact is still surfaced
    r = estimate_invariant_strength(_anchor(), addressed=None, oracle_strength="structural_ok")
    assert r["invariant_strength"] == "unknown" and r["asserted"] is True
    assert "coverage_unavailable" in r["reasons"]


def test_strength_unknown_when_assertion_strength_unknown():
    r = estimate_invariant_strength(_anchor(), addressed=True, oracle_strength=None)
    assert r["invariant_strength"] == "unknown" and r["asserted"] is None
    assert "assertion_strength_unknown" in r["reasons"]


def test_strength_exception_kind_uses_assertThrows_when_names_available():
    exc = InvariantDescriptor(statement="expired -> throws", kind="exception", source="manifest")
    yes = estimate_invariant_strength(exc, addressed=True, assertion_names=["assertThrows"])
    assert yes["asserted"] is True and yes["invariant_strength"] == "asserted_unpinned"
    no = estimate_invariant_strength(exc, addressed=True, assertion_names=["assertEquals"])
    assert no["asserted"] is False and no["invariant_strength"] == "addressed_unasserted"


def test_pinned_is_never_emitted_in_s2():
    # exhaustively: no S2 input combination yields "pinned" (that requires mutation, S3)
    for addr in (True, False, None):
        for os_ in ("none", "weak", "mixed", "structural_ok", "unknown", None):
            r = estimate_invariant_strength(_anchor(), addressed=addr, oracle_strength=os_)
            assert r["invariant_strength"] in INVARIANT_STRENGTHS
            assert r["invariant_strength"] != "pinned"


# --- S2 view + wire-in (advisory; verdict never changes) ------------------------

def test_view_verify_true_computes_per_invariant_strength():
    view = invariant_review_view(
        [_anchor(), InvariantDescriptor(statement="m", source="model")],
        verify=True, oracle_strength="structural_ok", addressed=True,
    )
    a, m = view["invariants"]
    assert a["verified"]["invariant_strength"] == "asserted_unpinned"   # anchoring
    assert m["verified"]["invariant_strength"] == "unknown"             # model cannot self-certify
    assert view["auto_accept_blocked"] is True                          # still never accepts


def test_view_verify_false_is_unchanged_s1_behavior():
    view = invariant_review_view([_anchor()])                            # verify defaults False
    assert view["invariants"][0]["verified"] is None


def test_review_summary_s2_uses_oracle_strength():
    from app.benchmark.models import BenchCase
    from app.benchmark.runner import _review_summary_with_rubric

    case = BenchCase(repo_url="u", target_class="C", invariants=[_anchor()])
    rs = {"oracle_strength_estimate": {"oracle_strength": "structural_ok"}}
    item = _review_summary_with_rubric(rs, case)["invariant_review"]["invariants"][0]
    assert item["verified"]["asserted"] is True                         # reused oracle_strength
    # coverage off in the benchmark -> addressed unknown -> strength unknown, asserted still shown
    assert item["verified"]["invariant_strength"] == "unknown"


# --- S3: line-scoped mutation -> pinned (gated semantic) -------------------------

def test_strength_pinned_when_all_scoped_mutants_killed():
    r = estimate_invariant_strength(_anchor(), addressed=True, oracle_strength="structural_ok",
                                    scoped_mutation_score=1.0)
    assert r["invariant_strength"] == "pinned" and r["scoped_mutation_score"] == 1.0


def test_strength_survivor_stays_unpinned_not_condemned():
    # a surviving scoped mutant could be a real gap OR an equivalent mutant (docs/46 §16):
    # S3 keeps it asserted_unpinned and flags it for explanation -- it does NOT condemn the test.
    r = estimate_invariant_strength(_anchor(), addressed=True, oracle_strength="structural_ok",
                                    scoped_mutation_score=0.5)
    assert r["invariant_strength"] == "asserted_unpinned"
    assert "scoped_mutants_survive" in r["reasons"]


def test_pinned_requires_addressed_and_asserted_not_just_mutation():
    # mutation alone never pins without reachability + a real assertion
    assert estimate_invariant_strength(_anchor(), addressed=False,
                                       scoped_mutation_score=1.0)["invariant_strength"] == "unaddressed"
    assert estimate_invariant_strength(_anchor(), addressed=True, oracle_strength="none",
                                       scoped_mutation_score=1.0)["invariant_strength"] == "addressed_unasserted"


def test_view_with_mutations_scopes_per_invariant_and_can_pin():
    inv = InvariantDescriptor(statement="add is exact", kind="boundary", source="manifest",
                              target_lines="4", target_method="add")
    rows = [
        {"line": 4, "method": "add", "status": "KILLED", "mutator": "MathMutator", "detected": True},
        {"line": 5, "method": "max", "status": "SURVIVED", "mutator": "CB", "detected": False},
    ]
    v = invariant_review_view([inv], verify=True, oracle_strength="structural_ok",
                              addressed=True, mutations=rows)["invariants"][0]["verified"]
    assert v["scoped_mutation_score"] == 1.0 and v["invariant_strength"] == "pinned"


def test_non_anchoring_never_pinned_even_with_perfect_mutation():
    # anti-self-certification holds at the strongest signal: a model-declared invariant with all
    # mutants killed is STILL unknown -- it never self-certifies (docs/48 §2).
    inv = InvariantDescriptor(statement="x", source="model", target_lines="4")
    rows = [{"line": 4, "method": "add", "status": "KILLED", "mutator": "M", "detected": True}]
    v = invariant_review_view([inv], verify=True, oracle_strength="structural_ok",
                              addressed=True, mutations=rows)["invariants"][0]["verified"]
    assert v["invariant_strength"] == "unknown" and v["anchoring"] is False


# --- S3 live wire-in: mutation evidence implies coverage; runner re-scoping ------

def test_view_mutations_imply_addressed_and_can_pin_without_coverage():
    # coverage off (addressed=None) but a KILLED scoped mutant proves the test reaches the
    # lines -> addressed, and all-killed -> pinned (docs/48 S3 live wire-in).
    inv = InvariantDescriptor(statement="x", source="manifest", target_method="validate")
    rows = [{"line": 10, "method": "validate", "status": "KILLED", "mutator": "M", "detected": True}]
    v = invariant_review_view([inv], verify=True, oracle_strength="structural_ok",
                              addressed=None, mutations=rows)["invariants"][0]["verified"]
    assert v["addressed"] is True and v["invariant_strength"] == "pinned"


def test_view_all_no_coverage_scoped_is_unaddressed():
    inv = InvariantDescriptor(statement="x", source="manifest", target_method="validate")
    rows = [{"line": 10, "method": "validate", "status": "NO_COVERAGE", "mutator": "M", "detected": False}]
    v = invariant_review_view([inv], verify=True, oracle_strength="structural_ok",
                              addressed=None, mutations=rows)["invariants"][0]["verified"]
    assert v["addressed"] is False and v["invariant_strength"] == "unaddressed"


def test_attach_invariant_mutations_rescopes_to_pinned():
    from app.benchmark import runner as R
    from app.benchmark.models import BenchCase, BenchCaseResult
    from app.mutation.pit import MutationResult

    inv = InvariantDescriptor(statement="x", source="manifest", target_method="validate")
    case = BenchCase(repo_url="u", target_class="C", invariants=[inv])
    result = BenchCaseResult(name="c", repo_url="u", target_class="C",
                             conclusion="NEED_HUMAN_REVIEW", oracle_strength="structural_ok",
                             review_summary={"invariant_review": {"invariants": [{"verified": None}]}})
    mres = MutationResult(available=True, mutation_score=1.0,
                          mutations=[{"line": 1, "method": "validate", "status": "KILLED",
                                      "mutator": "M", "detected": True}])
    R._attach_invariant_mutations(result, case, mres)
    v = result.review_summary["invariant_review"]["invariants"][0]["verified"]
    assert v["invariant_strength"] == "pinned"
    assert result.conclusion == "NEED_HUMAN_REVIEW"           # verdict never changes


def test_attach_invariant_mutations_noop_without_rows_or_invariants():
    from app.benchmark import runner as R
    from app.benchmark.models import BenchCase, BenchCaseResult
    from app.mutation.pit import MutationResult

    rs = {"invariant_review": {"invariants": [{"verified": None}]}}
    # no mutation result -> no-op
    case = BenchCase(repo_url="u", target_class="C",
                     invariants=[InvariantDescriptor(statement="x", source="manifest")])
    r1 = BenchCaseResult(name="c", repo_url="u", target_class="C", review_summary=dict(rs))
    R._attach_invariant_mutations(r1, case, None)
    assert r1.review_summary == rs
    # no invariants on the case -> no-op even with rows
    r2 = BenchCaseResult(name="c", repo_url="u", target_class="C", review_summary=dict(rs))
    mres = MutationResult(available=True,
                          mutations=[{"line": 1, "method": "m", "status": "KILLED", "detected": True}])
    R._attach_invariant_mutations(r2, BenchCase(repo_url="u", target_class="C"), mres)
    assert r2.review_summary == rs
