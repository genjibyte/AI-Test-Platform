"""run_kind tests (P1-T3, docs/43). The load-bearing invariant: a fake client can
never yield 'real'. Offline: no model, no pipeline, no .env."""
import pytest

from app.benchmark.models import BenchCaseResult
from app.ledger.ingest import record_from_bench_case
from app.ledger.models import Provenance
from app.llm.run_kind import RUN_KINDS, resolve_run_kind


def test_default_derivation_real_vs_fake():
    assert resolve_run_kind(client_is_fake=False) == "real"
    assert resolve_run_kind(client_is_fake=True) == "fake"


def test_invariant_fake_client_can_never_be_real():
    # THE invariant (owner decision, docs/43 §3): a fake client labeled 'real' is an error.
    with pytest.raises(ValueError):
        resolve_run_kind(client_is_fake=True, override="real")


def test_overrides_are_validated_and_guarded():
    assert resolve_run_kind(client_is_fake=True, override="dryrun") == "dryrun"
    assert resolve_run_kind(client_is_fake=True, override="smoke") == "smoke"
    assert resolve_run_kind(client_is_fake=True, override="FAKE") == "fake"  # case-insensitive
    assert resolve_run_kind(client_is_fake=False, override="real") == "real"
    assert resolve_run_kind(client_is_fake=False, override="smoke") == "smoke"
    with pytest.raises(ValueError):
        resolve_run_kind(client_is_fake=False, override="bogus")
    # docs/53 added 'external' for submit_candidate; the generator path's
    # resolve_run_kind never returns it (validated in test_submit_candidate).
    assert set(RUN_KINDS) == {"real", "fake", "dryrun", "smoke", "external"}


def _case(run_kind):
    return BenchCaseResult(
        name="c", repo_url="u", target_class="C", gen_outcome="PASS",
        passed=True, run_kind=run_kind, conclusion="NEED_HUMAN_REVIEW",
    )


def test_run_kind_carries_into_ledger_record():
    prov = Provenance(author_type="platform_generator", author_id="m")
    assert record_from_bench_case(_case("real"), prov).run_kind == "real"
    assert record_from_bench_case(_case("fake"), prov).run_kind == "fake"
    assert record_from_bench_case(_case(None), prov).run_kind is None
