"""Benchmark data model + pure aggregation (Phase 2.5).

All fields are FACTS captured from the existing pipelines. No verdict beyond the
Phase 2 invariant (NEED_HUMAN_REVIEW). Repair/accept metrics are intentionally
left null — they belong to Phase 3/4.
"""
from __future__ import annotations

from collections import Counter
from typing import List, Optional

from pydantic import BaseModel, Field

# --- Failure taxonomy (Phase 2.5) ------------------------------------------
# One bucket per (repo, target) case. None == clean PASS. These are FACTS about
# what blocked the generated test, ordered roughly outermost (repo) to innermost
# (the test itself). COVERAGE is tracked separately (see coverage_status), since
# "no coverage" is a measurement state, not a test failure.
FAILURE_TYPES = (
    "REPO_NOT_BUILDABLE",     # baseline repo failed to build/judge at all
    "REPO_CLONE_FAILED",      # git mirror clone failed before judging
    "LLM_CONFIG_FAILED",      # provider/key/model setup failed before generation
    "PIPELINE_FAILED",        # generation short-circuited (target/context/write)
    "POLICY_PLUGIN_FAILURE",  # RAT/checkstyle/enforcer/license/... failed the build
    "JACOCO_CONFLICT",        # duplicate java.lang.$JaCoCo double-agent crash
    "COMPILE_FAILURE",        # generated test failed to compile
    "NO_TESTS",               # compiled & ran but produced no test cases
    "TEST_FAILURE",           # ran but had assertion failures / errors
    "BUILD_ERROR",            # other non-zero build (uncategorized)
    "NO_MAVEN",               # maven unavailable
)

# Coverage measurement state — orthogonal to the failure bucket. A clean PASS
# can still be COVERAGE_UNAVAILABLE (e.g. JaCoCo skipped to avoid the F2 conflict).
COVERAGE_AVAILABLE = "available"
COVERAGE_UNAVAILABLE = "unavailable"

# Log signatures used to un-mask build crashes that otherwise surface as
# NO_TESTS / BUILD_ERROR.
_JACOCO_SIGNS = ("java.lang.$JaCoCo", "jacoco.agent.rt", "InjectedClassRuntime")
_POLICY_PLUGINS = (
    "apache-rat-plugin",
    "maven-checkstyle-plugin",
    "maven-enforcer-plugin",
    "spotbugs-maven-plugin",
    "license-maven-plugin",
    "maven-pmd-plugin",
)


class BenchCase(BaseModel):
    """One (repo, target) benchmark task."""

    repo_url: str
    branch: Optional[str] = None
    commit: Optional[str] = None  # exact SHA pin (frozen manifest); reproducible
    ref: Optional[str] = None     # human label for the pin (tag/baseline), advisory
    target_class: str
    target_method: Optional[str] = None
    name: Optional[str] = None

    def label(self) -> str:
        return self.name or f"{self.target_class}#{self.target_method or '*'}"


class BenchCaseResult(BaseModel):
    """docs/07 §8 per-task record, filled from judge + generate runs."""

    name: str
    repo_url: str
    branch: Optional[str] = None
    commit_hash: Optional[str] = None
    target_class: str
    target_method: Optional[str] = None

    # baseline (Phase 1)
    repo_judged: bool = False
    baseline_build_outcome: Optional[str] = None
    baseline_tests_green: Optional[bool] = None
    baseline_line_rate: Optional[float] = None
    baseline_branch_rate: Optional[float] = None

    # generation (Phase 2)
    generation_status: Optional[str] = None  # GEN_DONE / GEN_FAILED / REPO_NOT_BUILDABLE
    gen_outcome: Optional[str] = None         # PASS / COMPILE_FAILURE / ...
    compiled: Optional[bool] = None
    executed: Optional[bool] = None
    passed: Optional[bool] = None
    target_line_delta: Optional[float] = None
    target_branch_delta: Optional[float] = None
    coverage_dropped: Optional[bool] = None
    target_improved: Optional[bool] = None

    failure_type: Optional[str] = None        # bucket (FAILURE_TYPES); None when PASS
    coverage_status: str = COVERAGE_UNAVAILABLE  # available | unavailable
    production_code_touched: Optional[bool] = None
    model: Optional[str] = None
    conclusion: Optional[str] = None
    repair_rounds: Optional[int] = None
    repair_final_outcome: Optional[str] = None
    quality_gate_status: Optional[str] = None
    quality_blockers: int = 0
    quality_warnings: int = 0
    review_recommendation: Optional[str] = None  # Phase 4 advisory triage (docs/22)
    runtime_ms: int = 0
    error: Optional[str] = None


class BenchReport(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None
    generated_at: str = ""
    maven: Optional[str] = None
    cases: List[BenchCaseResult] = Field(default_factory=list)
    aggregate: dict = Field(default_factory=dict)


def classify_failure(
    repo_judged: bool,
    generation_status: Optional[str],
    gen_outcome: Optional[str],
    log_text: str = "",
) -> Optional[str]:
    """Map a case to one failure bucket (None == clean PASS).

    The build log is consulted FIRST because a JaCoCo agent crash or a policy
    plugin failure aborts the run and otherwise masquerades as NO_TESTS or a
    generic BUILD_ERROR. ``log_text`` may be empty (then only the coarse
    gen_outcome is used).
    """
    if not repo_judged:
        return "REPO_NOT_BUILDABLE"
    if generation_status == "GEN_FAILED":
        return "PIPELINE_FAILED"
    text = log_text or ""
    if any(s in text for s in _JACOCO_SIGNS):
        return "JACOCO_CONFLICT"
    if "Failed to execute goal" in text and any(p in text for p in _POLICY_PLUGINS):
        return "POLICY_PLUGIN_FAILURE"
    if gen_outcome == "PASS":
        return None
    return gen_outcome  # COMPILE_FAILURE / TEST_FAILURE / NO_TESTS / BUILD_ERROR / NO_MAVEN


def _rate(rows: List[BenchCaseResult], pred) -> Optional[float]:
    if not rows:
        return None
    return round(sum(1 for r in rows if pred(r)) / len(rows), 4)


def aggregate(cases: List[BenchCaseResult]) -> dict:
    """Aggregate metrics (docs/07 §8). Rates are over generation-ATTEMPTED cases
    (i.e. repos that judged), so an unbuildable repo doesn't dilute compile rate."""
    n = len(cases)
    attempted = [c for c in cases if c.repo_judged]
    failures = Counter(c.failure_type for c in cases if c.failure_type)
    setup_failures = sum(1 for c in cases if c.failure_type == "LLM_CONFIG_FAILED")
    clone_failures = sum(1 for c in cases if c.failure_type == "REPO_CLONE_FAILED")
    repo_build_failures = sum(
        1 for c in cases if c.failure_type == "REPO_NOT_BUILDABLE"
    )
    runtimes = [c.runtime_ms for c in cases]
    repair_round_values = [
        c.repair_rounds for c in attempted if c.repair_rounds is not None
    ]
    quality_checked = [c for c in attempted if c.quality_gate_status is not None]
    return {
        "total_cases": n,
        "repos": len({c.repo_url for c in cases}),
        "buildable_repos": len({c.repo_url for c in cases if c.repo_judged}),
        "setup_failures": setup_failures,
        "clone_failures": clone_failures,
        "repo_build_failures": repo_build_failures,
        "generation_attempted": len(attempted),
        "compile_pass_rate": _rate(attempted, lambda c: c.compiled is True),
        "gen_test_pass_rate": _rate(attempted, lambda c: c.passed is True),
        "coverage_measured": sum(
            1 for c in attempted if c.coverage_status == COVERAGE_AVAILABLE
        ),
        "coverage_improved_rate": _rate(
            [c for c in attempted if c.coverage_status == COVERAGE_AVAILABLE],
            lambda c: c.target_improved is True,
        ),
        "coverage_not_dropped_rate": _rate(
            [c for c in attempted if c.coverage_status == COVERAGE_AVAILABLE],
            lambda c: c.coverage_dropped is False,
        ),
        "need_human_review_rate": _rate(
            attempted, lambda c: c.conclusion == "NEED_HUMAN_REVIEW"
        ),
        "top_failure_types": dict(failures.most_common()),
        "avg_runtime_ms": int(sum(runtimes) / n) if n else 0,
        # Phase 3/4 review metrics. accept_rate stays null: the platform still
        # does not auto-accept generated tests.
        "average_repair_rounds": (
            round(sum(repair_round_values) / len(repair_round_values), 2)
            if repair_round_values else None
        ),
        "quality_gate_pass_rate": _rate(
            quality_checked, lambda c: c.quality_gate_status == "PASS"
        ),
        "quality_gate_failures": sum(
            1 for c in quality_checked if c.quality_gate_status == "FAIL"
        ),
        "quality_gate_reviews": sum(
            1 for c in quality_checked if c.quality_gate_status == "REVIEW"
        ),
        # Phase 4 advisory triage distribution over generation-attempted cases.
        "recommendation_distribution": dict(
            Counter(
                c.review_recommendation
                for c in attempted
                if c.review_recommendation is not None
            ).most_common()
        ),
        "accept_rate": None,
    }


def load_spec(data: dict) -> List[BenchCase]:
    """Parse a spec dict ({"cases": [...]}) into BenchCase objects."""
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("spec must contain a non-empty 'cases' list")
    return [BenchCase(**c) for c in cases]
