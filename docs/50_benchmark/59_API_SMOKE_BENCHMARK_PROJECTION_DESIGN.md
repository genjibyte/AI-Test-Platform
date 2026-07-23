# 59 - API Smoke Benchmark Projection Design

> Date: 2026-07-21
> Status: S9A pure projection helper, S9B conditional markdown rendering, and S9C red-line
> descriptive counts are live. No benchmark schema change, ledger schema change, SQLite index,
> executor, dependency, external SUT import, digest severity, verdict change, `trusted=True`, or
> auto-accept is implied.
>
> Upstream: `docs/60_api_candidate/09_S8_API_SMOKE_DENOMINATOR_POLICY.md`,
> `docs/50_benchmark/43_RUN_KIND_DESIGN.md`,
> `docs/50_benchmark/56_REAL_WORLD_VALIDATION_LINE.md`, and
> `docs/00_foundation/54_CORE_FREEZE_AND_BOUNDARY_REFERENCE.md`.

## 0. Purpose

S8 now emits a report-only block:

```text
review_summary["api_smoke_denominator"]
```

That block says whether a manifest-bound `junit_api_candidate` row has enough local evidence to
be a future API smoke denominator row. S8 intentionally does not count the row in benchmark or
ledger.

This document specifies the benchmark-side projection that counts API smoke denominator facts
without mixing them into the current Java/Maven unit-test headline.

The projection answers:

- how many rows carry API smoke denominator facts;
- how many of those rows are denominator-ready under S8;
- which `run_kind`, `smoke_id`, candidate kind, and requirement failures explain the shape;
- which existing S8C API smoke red-line review flags appear in those rows;
- what existing judge outcomes those rows had.

It does not answer whether the candidate is useful, accepted, defect-revealing, or safe to merge.

## 1. Core Decision

S9A V1 adds a pure benchmark helper, separate from `aggregate(...)`:

```text
app/benchmark/api_smoke_projection.py

api_smoke_benchmark_projection(cases, *, view="raw" | "headline") -> dict
```

The helper reads existing `BenchCaseResult.review_summary` data only. It does not add
`BenchCaseResult` fields, mutate reports, write ledger rows, start services, execute API clients,
or change review decisions.

Do not add new keys to the existing `aggregate(...)` result. The current aggregate remains the
unit-test benchmark aggregate. API smoke gets its own named projection.

## 2. Source Rows

An API smoke source row is any benchmark case whose review summary contains:

```text
review_summary["api_smoke_denominator"]["policy_version"] == "api_smoke_denominator.v1"
review_summary["api_smoke_denominator"]["scope"] == "separate_api_smoke_denominator"
```

Rows without that block are ignored by this projection.

The source block remains advisory and report-only. S9A benchmark projection is the only sanctioned
place that counts these facts; generic aggregate, ledger analytics, digest, and review verdicts
must not read them.

## 3. RAW View

The RAW view includes every API smoke source row, regardless of `run_kind` and regardless of
S8 eligibility:

```text
view = "raw"
included rows = rows with review_summary["api_smoke_denominator"]
run_kind filter = none
```

RAW is for diagnosis and drift detection. It can show fake, dryrun, smoke, external, real, and
historical unknown rows, but it must label the view as all run kinds.

Minimum RAW fields:

```text
projection_version: "api_smoke_benchmark_projection.v1"
view: "raw"
source_policy_version: "api_smoke_denominator.v1"
total_cases_seen
api_smoke_source_rows
eligible_source_rows
ineligible_source_rows
by_run_kind
by_candidate_kind
by_smoke_id
not_eligible_reason_counts
requirement_failure_counts
redline_flag_counts
redlines_satisfied_distribution
gen_outcome_distribution
quality_gate_distribution
review_recommendation_distribution
need_human_review_cases
trusted_true_cases
unit_headline_eligible_cases
note
```

Run-kind authority:

```text
by_run_kind uses BenchCaseResult.run_kind
```

The S8 denominator block also carries a `run_kind` copy, but S9A must not let that copy override
the benchmark row's top-level `run_kind`. If `BenchCaseResult.run_kind` is missing, the row is
`unknown` for this projection even when the denominator copy says `external` or `real`.

Expected invariants:

```text
unit_headline_eligible_cases == 0
trusted_true_cases == 0
```

If either value is non-zero, the projection should surface it as an invariant warning in the
projection dict and markdown text. It still must not change a verdict.

## 4. API Smoke HEADLINE View

The API smoke HEADLINE view is separate from the existing unit-test `HEADLINE(real)` view.

```text
view = "headline"
included rows =
  rows with review_summary["api_smoke_denominator"]
  and eligible_for_api_smoke_denominator == true
  and BenchCaseResult.run_kind in {"real", "external"}
```

Why include `external`: public `submit_candidate` rows are intentionally forced to
`run_kind="external"`. For API smoke, that is a valid producer-agnostic candidate source, not a
model-quality headline. Therefore:

```text
unit-test headline = run_kind == "real"
API smoke headline = S8 eligible and BenchCaseResult.run_kind in {"real", "external"}
```

Excluded from API smoke HEADLINE:

```text
fake
dryrun
smoke
unknown / null / historical rows
ineligible S8 rows
rows without api_smoke_denominator
rows whose top-level BenchCaseResult.run_kind is missing, even if the denominator copy has a value
```

The title must make this distinction visible:

```text
API smoke denominator - HEADLINE (S8 eligible; real/external only)
```

Do not title it `Aggregate - HEADLINE`. That phrase belongs to the current benchmark aggregate and
would invite accidental comparison with unit-test model-quality metrics.

## 5. Relationship To S8 Flags

S8 source reports keep:

```text
benchmark_counting_enabled = false
unit_headline_eligible = false
```

The first flag means S8 rows are not counted by any generic benchmark path. S9A counts the same
source facts only inside the explicitly named API smoke projection.
Do not flip the source report flag merely to render this projection.

The second flag is stronger: API smoke rows must never enter the current unit-test headline.

## 6. Markdown Rendering Shape

S9B renders markdown only when the RAW projection has at least one API smoke source row:

```text
render sections only if api_smoke_benchmark_projection(report.cases)["api_smoke_source_rows"] > 0
```

This avoids polluting ordinary unit-test benchmark reports with empty API smoke sections.

S9B adds two sections after the real-world validation line and before survived-mutant/per-case
rows:

```text
## API smoke denominator - RAW (all run_kinds)

- source_rows: ...
- eligible_source_rows: ...  ineligible_source_rows: ...
- by_run_kind: ...
- by_smoke_id: ...
- not_eligible_reason_counts: ...
- redline_flag_counts: ...
- redlines_satisfied_distribution: ...
- gen_outcome_distribution: ...
- quality_gate_distribution: ...
  invariant_warnings: ...
  (advisory; API smoke projection does not affect aggregate headlines or review conclusion)

## API smoke denominator - HEADLINE (S8 eligible; real/external only)

- headline_rows: ...
- by_run_kind: ...
- by_smoke_id: ...
- redline_flag_counts: ...
- redlines_satisfied_distribution: ...
- gen_outcome_distribution: ...
- review_recommendation_distribution: ...
  invariant_warnings: ...
  (candidate-evaluation view; not a model-quality or auto-accept metric)
```

The markdown must not alter:

```text
Aggregate - RAW
Aggregate - HEADLINE (real only; fake/dryrun/smoke/external/unknown excluded)
Business tags
Oracle strength
Asset Gate
Real-world validation line
Per-case table
```

## 7. Metrics Boundary

Allowed automated evidence:

```text
run_kind
smoke_id
candidate_kind
eligible_for_api_smoke_denominator
not_eligible_reasons
requirements true/false/null
gen_outcome
quality_gate_status
review_recommendation
conclusion == NEED_HUMAN_REVIEW
trusted == False
api_smoke_redlines.review_flags
api_smoke_redlines.redlines_satisfied
```

Not allowed in S9:

```text
usable_test_rate
defect_discovery_rate
human_handling_time
diagnosis_time
misjudgment_rate
accept_rate
auto-accept
auto-adoption
API correctness score without human/golden labels
```

API smoke HEADLINE may report existing automated judge outcomes for eligible rows. It must not call
green execution "valuable" or "usable".

## 8. Tests Live

S9A pure helper tests are live:

```text
tests/test_api_smoke_benchmark_projection.py
  raw ignores ordinary unit rows and includes all api_smoke_denominator rows
  raw counts eligible and ineligible S8 rows
  raw groups by run_kind, smoke_id, candidate_kind, not_eligible_reasons, and failed requirements
  headline includes eligible external rows
  headline includes eligible real rows
  headline excludes fake, dryrun, smoke, null, and historical unknown rows
  headline excludes top-level run_kind unknown even when denominator copy says external
  headline excludes S8-ineligible external/real rows
  unit_headline_eligible_cases stays zero
  trusted_true_cases surfaces an invariant warning but does not change verdict
  aggregate(...) keys and values stay unchanged
```

S9A audit notes, 2026-07-21:

```text
resolved:
  HEADLINE filtering now uses BenchCaseResult.run_kind only; denominator.run_kind cannot promote an
  unknown top-level run_kind into headline.
covered:
  source-row selection, RAW counts, HEADLINE run_kind filter, failed requirement counts,
  not_eligible_reasons, invariant warnings, and aggregate(...) non-drift.
residual:
  no ledger projection, no executor, no external asset use.
```

S9B markdown tests are live in `tests/test_benchmark.py`:

```text
  omits API smoke sections when no api_smoke_denominator source rows exist
  renders API smoke RAW and API smoke HEADLINE under distinct titles when source rows exist
  raw section includes all API smoke source rows
  headline section includes eligible real/external rows only
  keeps Aggregate HEADLINE excluding external submit rows
  keeps api_smoke fields out of aggregate(...)
  does not add accept_rate or auto-accept language
  places API smoke sections after validation-line sections and before survived-mutant/per-case rows
```

S9B render audit notes, 2026-07-21:

```text
covered:
  conditional omission on ordinary unit-test benchmark reports, distinct RAW/HEADLINE titles,
  current unit-test Aggregate HEADLINE non-drift, no aggregate(...) key drift, no accept_rate
  language in API smoke sections, and markdown placement after validation-line sections and before
  survived-mutant/per-case rows.
residual:
  no ledger projection, no executor, no external asset use.
```

S9C red-line count tests are live in `tests/test_api_smoke_benchmark_projection.py` and
`tests/test_benchmark.py`:

```text
  counts existing api_smoke_redlines.review_flags in the named API smoke projection only
  reports redlines_satisfied_distribution as true / false / absent / unknown buckets
  HEADLINE red-line counts include only S8-eligible real/external rows
  fake and S8-ineligible red-line flags remain visible only in RAW
  renders red-line counts in conditional API smoke benchmark markdown sections
  keeps api_smoke_redlines fields out of aggregate(...)
```

S9C audit notes, 2026-07-22:

```text
covered:
  red-line flag counts and satisfied buckets are projections of already emitted S8C report facts;
  they do not recompute red-line policy, change generic aggregate keys, create ledger fields,
  affect digest severity, or change conclusion/trust authority.
residual:
  no ledger projection change, no executor, no external asset use.
```

No test may start a service, Docker container, external API executor, real model, or networked SUT.

## 9. Implementation Slices

Recommended bounded order:

```text
S9A pure projection helper + tests - live
  no aggregate key, no ledger

S9B markdown rendering of the projection - live
  still no aggregate key or ledger
  render nothing when there are no API smoke source rows

S9C red-line descriptive counts in benchmark projection + markdown - live
  counts only existing api_smoke_redlines report facts inside the named projection
  still no aggregate key, ledger change, digest signal, or verdict change

S10A API smoke compact ledger carry - live
  drafted in docs/50_benchmark/60_API_SMOKE_LEDGER_PROJECTION_DESIGN.md
  compact JudgedRecord JSON carry only; no existing analytics changes

S10B API smoke ledger projection helper - live
  named pure helper only; separate from existing ledger_summary / aggregate_badcases
```

Stop before any executor, dependency, external SUT import, digest severity, verdict, or auto-accept
work unless the owner explicitly approves a separate design.

## 10. External Asset Mapping

External Asset Mapping:

```text
assets consulted: none for S9A/S9B/S9C V1
intake shape chosen: none
project artifact affected: app/benchmark/api_smoke_projection.py, app/benchmark/report_md.py,
  tests/test_api_smoke_benchmark_projection.py, tests/test_benchmark.py
expected evidence: local report fields already emitted by the judge
red lines: no external asset execution, no SUT import, no dependency, no executor
```

## 11. Real-World Validation Impact

```text
Real-World Validation Impact:
- metrics strengthened:
  separate API smoke denominator discipline; producer-agnostic candidate evaluation visibility
- automated evidence:
  S8 denominator eligibility, run_kind, smoke_id, candidate_kind, requirement failures, existing
  API smoke red-line report flags, Maven/Surefire judge outcome, quality gate status, advisory
  recommendation, conclusion/trust invariants
- human labels required:
  yes for usable-test rate, defect discovery, diagnosis time, human handling time, and misjudgment
  rate; no for denominator eligibility facts
- denominator:
  RAW = all rows with api_smoke_denominator; HEADLINE = S8 eligible rows with run_kind real/external
- headline eligibility:
  separate API smoke headline only; never current unit-test real headline
- red lines:
  no executor, no dependency, no ledger/schema/index change, no digest severity, no auto-accept,
  no trusted=True, no claim that green API smoke equals engineering value
```

## 12. Definition Of Done

This design is sufficient if the next maintainer can answer:

- why API smoke RAW and API smoke HEADLINE are separate views;
- why `external` is excluded from unit-test headline but included in API smoke headline;
- why `benchmark_counting_enabled=false` in S8 does not authorize generic aggregate counting;
- why `unit_headline_eligible=false` must stay true for every API smoke row;
- which fields can be counted without human labels;
- why ledger carry implementation is a later owner-approved slice, not a side effect of benchmark
  rendering.
