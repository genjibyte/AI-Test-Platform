"""Render a BenchReport to Markdown (docs/07 §8 style). Pure formatting."""
from __future__ import annotations

from app.benchmark.api_smoke_projection import api_smoke_benchmark_projection
from app.benchmark.models import (
    BenchReport,
    aggregate,
    asset_gate_breakdown,
    business_breakdown,
    oracle_strength_breakdown,
)
from app.benchmark.validation_line import validation_line_summary


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


def _oracle_lines(bd: dict, title: str) -> list:
    """Advisory oracle-strength group-by (docs/46 S2). STRUCTURAL counts only; un-analyzed
    -> unknown. Semantic strength stays human review."""
    return [
        f"## {title}",
        "",
        f"- analyzed total: {bd.get('total')}  (run_kind_filter: {bd.get('run_kind_filter')})",
        f"- by_oracle_strength: {bd.get('by_oracle_strength')}",
        "  (structural estimate only; semantic strength stays human review)",
        "",
    ]


def _asset_gate_lines(bd: dict, title: str) -> list:
    """Descriptive Asset Gate group-by (docs/55 S3D). Advisory counts only."""
    return [
        f"## {title}",
        "",
        f"- total: {bd.get('total')}  (run_kind_filter: {bd.get('run_kind_filter')})",
        f"- by_test_level: {bd.get('by_test_level')}",
        f"- missing_asset_cases: {bd.get('missing_asset_cases')}  "
        f"missing_assets_total: {bd.get('missing_assets_total')}",
        f"- partial_asset_cases: {bd.get('partial_asset_cases')}  "
        f"partial_assets_total: {bd.get('partial_assets_total')}",
        "  (advisory; Asset Gate does not change aggregate headlines or review conclusion)",
        "",
    ]


def _validation_lines(summary: dict, title: str) -> list:
    """Real-world validation-line V1 summary (docs/56). Automated evidence only."""
    return [
        f"## {title}",
        "",
        f"- total_cases: {summary.get('total_cases')}  "
        f"generation_attempted: {summary.get('generation_attempted')}  "
        f"first_run_evidence_cases: {summary.get('first_run_evidence_cases')}  "
        f"(run_kind_filter: {summary.get('run_kind_filter')})",
        f"- first_compile_pass_rate: {_pct(summary.get('first_compile_pass_rate'))}  "
        f"first_compile_pass_count: {summary.get('first_compile_pass_count')}",
        f"- first_test_pass_rate: {_pct(summary.get('first_test_pass_rate'))}  "
        f"first_test_pass_count: {summary.get('first_test_pass_count')}",
        f"- structural_weak_signal_rate: {_pct(summary.get('structural_weak_signal_rate'))}  "
        f"structural_weak_signal_cases: {summary.get('structural_weak_signal_cases')}/"
        f"{summary.get('structural_weak_signal_evaluated_cases')}",
        f"- preflight_reject_cases: {summary.get('preflight_reject_cases')}  "
        "first_run_ambiguous_due_to_repair: "
        f"{summary.get('first_run_ambiguous_due_to_repair')}",
        "  (V1 automated evidence only; human/golden metrics remain unavailable)",
        "",
    ]


def _api_smoke_lines(summary: dict, title: str, footer: str) -> list:
    """API smoke denominator projection (docs/59 S9B). Advisory counts only."""
    return [
        f"## {title}",
        "",
        f"- source_rows: {summary.get('api_smoke_source_rows')}  "
        f"projected_rows: {summary.get('projected_rows')}  "
        f"(run_kind_filter: {summary.get('run_kind_filter')})",
        f"- eligible_source_rows: {summary.get('eligible_source_rows')}  "
        f"ineligible_source_rows: {summary.get('ineligible_source_rows')}",
        f"- by_run_kind: {summary.get('by_run_kind')}",
        f"- by_smoke_id: {summary.get('by_smoke_id')}",
        f"- by_candidate_kind: {summary.get('by_candidate_kind')}",
        f"- not_eligible_reason_counts: {summary.get('not_eligible_reason_counts')}",
        f"- requirement_failure_counts: {summary.get('requirement_failure_counts')}",
        f"- redline_flag_counts: {summary.get('redline_flag_counts')}",
        f"- redlines_satisfied_distribution: "
        f"{summary.get('redlines_satisfied_distribution')}",
        f"- gen_outcome_distribution: {summary.get('gen_outcome_distribution')}",
        f"- quality_gate_distribution: {summary.get('quality_gate_distribution')}",
        "- review_recommendation_distribution: "
        f"{summary.get('review_recommendation_distribution')}",
        f"- need_human_review_cases: {summary.get('need_human_review_cases')}  "
        f"trusted_true_cases: {summary.get('trusted_true_cases')}  "
        f"unit_headline_eligible_cases: {summary.get('unit_headline_eligible_cases')}",
        f"- invariant_warnings: {summary.get('invariant_warnings')}",
        f"  ({footer})",
        "",
    ]


def _api_smoke_sections(report: BenchReport) -> list:
    """Render nothing for ordinary unit-test benchmark reports with no API smoke rows."""
    raw = api_smoke_benchmark_projection(report.cases)
    if raw.get("api_smoke_source_rows", 0) <= 0:
        return []
    headline = api_smoke_benchmark_projection(report.cases, view="headline")
    return (
        _api_smoke_lines(
            raw,
            "API smoke denominator - RAW (all run_kinds)",
            "advisory; API smoke projection does not affect aggregate headlines "
            "or review conclusion",
        )
        + _api_smoke_lines(
            headline,
            "API smoke denominator - HEADLINE (S8 eligible; real/external only)",
            "candidate-evaluation view; not a model-quality or auto-accept metric",
        )
    )


def _survivor_lines(report: BenchReport) -> list:
    """Aggregate survived-mutant classification across cases (docs/49 S2). Advisory: explains
    survivors (coverage gap vs weak oracle vs maybe-equivalent); never a verdict. Rendered only
    when a gated mutation run produced per-mutation rows (else omitted entirely)."""
    agg = {"not_covered": 0, "survived_weak_oracle": 0,
           "survived_maybe_equivalent": 0, "survived_unclassified": 0}
    total = 0
    for c in report.cases:
        ms = (c.review_summary or {}).get("mutation_survivors") if c.review_summary else None
        if not ms:
            continue
        for k in agg:
            agg[k] += (ms.get("counts") or {}).get(k, 0)
        total += ms.get("total_survivors", 0)
    if total == 0:
        return []
    return [
        "## Survived mutants — classification (advisory)",
        "",
        f"- total_survivors: {total}",
        f"- by_category: {agg}",
        "  (advisory; survival is not proof a test is weak — equivalence is undecidable)",
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
        "Aggregate — HEADLINE (real only; fake/dryrun/smoke/external/unknown excluded)",
    )
    lines += _business_lines(
        business_breakdown(report.cases), "Business tags — RAW (all run_kinds)"
    )
    lines += _business_lines(
        business_breakdown(report.cases, run_kind="real"), "Business tags — HEADLINE (real only)"
    )
    lines += _oracle_lines(
        oracle_strength_breakdown(report.cases), "Oracle strength — RAW (all run_kinds)"
    )
    lines += _oracle_lines(
        oracle_strength_breakdown(report.cases, run_kind="real"),
        "Oracle strength — HEADLINE (real only)",
    )
    lines += _asset_gate_lines(
        asset_gate_breakdown(report.cases), "Asset Gate - RAW (all run_kinds)"
    )
    lines += _asset_gate_lines(
        asset_gate_breakdown(report.cases, run_kind="real"),
        "Asset Gate - HEADLINE (real only)",
    )
    lines += _validation_lines(
        validation_line_summary(report.cases),
        "Real-world validation line - RAW (all run_kinds)",
    )
    lines += _validation_lines(
        validation_line_summary(report.cases, run_kind="real"),
        "Real-world validation line - HEADLINE (real only)",
    )
    lines += _api_smoke_sections(report)
    lines += _survivor_lines(report)
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
