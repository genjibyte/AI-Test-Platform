"""Render a BenchReport to Markdown (docs/07 §8 style). Pure formatting."""
from __future__ import annotations

from app.benchmark.models import BenchReport, aggregate, business_breakdown


def _pct(v) -> str:
    return "—" if v is None else f"{v * 100:.0f}%"


def _f(v) -> str:
    return "—" if v is None else (f"{v:+.4f}" if isinstance(v, float) else str(v))


def _plain(v) -> str:
    return "—" if v is None else str(v)


def _aggregate_lines(a: dict, title: str) -> list:
    """Render one aggregate dict. Same shape for RAW and the real headline (docs/43 S2)."""
    return [
        f"## {title}",
        "",
        f"- total_cases: {a.get('total_cases')}  repos: {a.get('repos')}  "
        f"buildable_repos: {a.get('buildable_repos')}  "
        f"generation_attempted: {a.get('generation_attempted')}",
        f"- setup_failures: {a.get('setup_failures', 0)}  "
        f"clone_failures: {a.get('clone_failures', 0)}  "
        f"repo_build_failures: {a.get('repo_build_failures', 0)}",
        f"- compile_pass_rate: {_pct(a.get('compile_pass_rate'))}  "
        f"gen_test_pass_rate: {_pct(a.get('gen_test_pass_rate'))}",
        f"- coverage_measured: {a.get('coverage_measured')}/"
        f"{a.get('generation_attempted')}  "
        f"coverage_improved_rate: {_pct(a.get('coverage_improved_rate'))}  "
        f"coverage_not_dropped_rate: {_pct(a.get('coverage_not_dropped_rate'))}",
        f"- need_human_review_rate: {_pct(a.get('need_human_review_rate'))}  "
        f"avg_runtime_ms: {a.get('avg_runtime_ms')}",
        f"- top_failure_types: {a.get('top_failure_types')}",
        f"- average_repair_rounds: {_plain(a.get('average_repair_rounds'))}  "
        f"quality_gate_pass_rate: {_pct(a.get('quality_gate_pass_rate'))}  "
        f"quality_gate_failures: {a.get('quality_gate_failures', 0)}  "
        "accept_rate: —",
        f"- recommendation_distribution: {a.get('recommendation_distribution', {})}  "
        "(advisory; conclusion stays NEED_HUMAN_REVIEW)",
        "",
    ]


def _business_lines(bd: dict, title: str) -> list:
    """Descriptive business-tag group-by (docs/45 S2). Counts only; untagged -> unknown."""
    return [
        f"## {title}",
        "",
        f"- tagged total: {bd.get('total')}  (run_kind_filter: {bd.get('run_kind_filter')})",
        f"- by_domain: {bd.get('by_domain')}",
        f"- by_pattern: {bd.get('by_pattern')}",
        "",
    ]


def render_markdown(report: BenchReport) -> str:
    # Headline (real-only) is recomputed from the cases so fake/dryrun/smoke and
    # historical (unknown run_kind) rows never inflate model-quality numbers (docs/43 S2).
    lines = [
        "# Real-Repo Benchmark Report",
        "",
        f"- provider: `{report.provider}`  model: `{report.model}`",
        f"- generated_at: {report.generated_at}",
        f"- maven: `{report.maven}`",
        "",
    ]
    lines += _aggregate_lines(report.aggregate, "Aggregate — RAW (all run_kinds)")
    lines += _aggregate_lines(
        aggregate(report.cases, run_kind="real"),
        "Aggregate — HEADLINE (real only; fake/dryrun/smoke/unknown excluded)",
    )
    lines += _business_lines(
        business_breakdown(report.cases), "Business tags — RAW (all run_kinds)"
    )
    lines += _business_lines(
        business_breakdown(report.cases, run_kind="real"), "Business tags — HEADLINE (real only)"
    )
    lines += [
        "## Per-case",
        "",
        "| case | judged | compiled | passed | failure | repair | quality | "
        "recommendation | coverage | tgt_branch_Δ | improved | ms |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for c in report.cases:
        lines.append(
            f"| {c.name} | {c.repo_judged} | "
            f"{c.compiled if c.compiled is not None else '—'} | "
            f"{c.passed if c.passed is not None else '—'} | "
            f"{c.failure_type or 'PASS'} | "
            f"{c.repair_rounds if c.repair_rounds is not None else '—'} | "
            f"{c.quality_gate_status or '—'}"
            f" ({c.quality_blockers}/{c.quality_warnings}) | "
            f"{c.review_recommendation or '—'} | "
            f"{c.coverage_status} | "
            f"{_f(c.target_branch_delta)} | "
            f"{c.target_improved if c.target_improved is not None else '—'} | "
            f"{c.runtime_ms} |"
        )
    lines.append("")
    return "\n".join(lines)
