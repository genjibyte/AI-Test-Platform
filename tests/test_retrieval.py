"""Badcase retrieval tests (docs/50 S1). Offline; pure; advisory -- retrieval surfaces real past
records as precedent and changes NO verdict (conclusion stays NEED_HUMAN_REVIEW).
"""
import uuid

from app.ledger.models import JudgedRecord, Provenance
from app.ledger.retrieval import find_similar, find_similar_in_store
from app.ledger.store import LedgerStore

_PROV = Provenance(author_type="platform_generator", author_id="m")


def _rec(target_class="com.x.Calc", target_method=None, failure_type=None,
         business_pattern=None, test_fingerprint=None, repo_url="u",
         conclusion="NEED_HUMAN_REVIEW", rid=None):
    return JudgedRecord(
        record_id=rid or str(uuid.uuid4()), repo_url=repo_url,
        target_class=target_class, target_method=target_method, provenance=_PROV,
        failure_type=failure_type, business_pattern=business_pattern,
        test_fingerprint=test_fingerprint, conclusion=conclusion,
    )


def test_same_target_method_ranks_first():
    recs = [
        _rec(target_class="com.x.Calc", target_method="max", rid="B"),   # same class
        _rec(target_class="com.x.Calc", target_method="add", rid="A"),   # same method
        _rec(target_class="com.y.Other", target_method="add", rid="C"),  # unrelated
    ]
    out = find_similar(recs, target_class="com.x.Calc", target_method="add")
    assert out[0]["record_id"] == "A" and "same_target_method" in out[0]["reasons"]
    assert out[0]["score"] > out[1]["score"]                 # A (+3) before B (+2)
    assert "C" not in [o["record_id"] for o in out]          # no signal -> excluded


def test_duplicate_fingerprint_is_flagged_and_weighted():
    recs = [
        _rec(target_class="com.z.Unrelated", test_fingerprint="fp123", rid="DUP"),
        _rec(target_class="com.x.Calc", target_method="add", rid="CLS"),
    ]
    out = find_similar(recs, target_class="com.x.Calc", target_method="add",
                       test_fingerprint="fp123")
    assert out[0]["record_id"] == "DUP"                      # +4 outranks same_method +3
    assert "duplicate_fingerprint" in out[0]["reasons"]


def test_same_simple_class_across_packages():
    recs = [_rec(target_class="com.other.Calc", rid="S")]    # same simple name, diff package
    out = find_similar(recs, target_class="com.x.Calc")
    assert out and out[0]["reasons"] == ["same_simple_class"] and out[0]["score"] == 1


def test_failure_type_and_business_pattern_boost():
    recs = [
        _rec(target_class="com.x.Calc", target_method="add", failure_type="COMPILE_FAILURE",
             business_pattern="money_bound", rid="X"),
    ]
    out = find_similar(recs, target_class="com.x.Calc", target_method="add",
                       failure_type="COMPILE_FAILURE", business_pattern="money_bound")
    r = out[0]
    assert r["score"] == 3 + 2 + 1                            # method + failure + pattern
    assert set(r["reasons"]) == {"same_target_method", "same_failure_type", "same_business_pattern"}
    assert r["failure_type"] == "COMPILE_FAILURE"


def test_empty_and_no_match_return_empty():
    assert find_similar([], target_class="com.x.Calc") == []
    assert find_similar([_rec(target_class="com.y.Z", repo_url="other")],
                        target_class="com.x.Calc") == []      # no shared signal


def test_top_k_limits_results():
    recs = [_rec(target_class="com.x.Calc", target_method="add", rid=f"r{i}") for i in range(7)]
    out = find_similar(recs, target_class="com.x.Calc", target_method="add", top_k=3)
    assert len(out) == 3


def test_retrieval_is_advisory_readonly():
    rec = _rec(target_class="com.x.Calc", target_method="add", conclusion="NEED_HUMAN_REVIEW")
    out = find_similar([rec], target_class="com.x.Calc", target_method="add")
    assert out[0]["conclusion"] == "NEED_HUMAN_REVIEW"        # surfaced read-only
    assert rec.conclusion == "NEED_HUMAN_REVIEW"              # input never mutated


def test_find_similar_in_store(tmp_path):
    store = LedgerStore(tmp_path / "ledger.db")
    store.append(_rec(target_class="com.x.Calc", target_method="add", rid="A"))
    store.append(_rec(target_class="com.y.Other", repo_url="other", rid="B"))
    out = find_similar_in_store(store, target_class="com.x.Calc", target_method="add")
    assert [o["record_id"] for o in out] == ["A"]            # only the relevant record


# --- S2: actionable precedent (derived signature + declared root-cause/fix) ------

def test_result_surfaces_signature_and_declared_root_cause():
    rec = JudgedRecord(
        record_id="R", repo_url="u", target_class="com.x.Calc", target_method="add",
        provenance=_PROV, failure_type="COMPILE_FAILURE",
        root_cause="missing import", fix_note="add import com.x.Helper",
        conclusion="NEED_HUMAN_REVIEW",
    )
    out = find_similar([rec], target_class="com.x.Calc", target_method="add")[0]
    assert out["signature"] == "COMPILE_FAILURE@com.x.Calc#add"   # derived "why"
    assert out["root_cause"] == "missing import"                  # declared "how" (advisory)
    assert out["fix_note"] == "add import com.x.Helper"


def test_precedent_fields_default_none_and_signature_none_when_no_failure():
    assert _rec().root_cause is None and _rec().fix_note is None
    out = find_similar([_rec(target_class="com.x.Calc", target_method="add")],
                       target_class="com.x.Calc", target_method="add")[0]
    assert out["signature"] is None                               # no failure_type -> no signature
    assert out["root_cause"] is None and out["fix_note"] is None
