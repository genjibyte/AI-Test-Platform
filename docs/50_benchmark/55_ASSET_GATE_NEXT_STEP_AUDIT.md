# 55 - Asset Gate Design Digest

> Date: 2026-07-04  
> Status: active design reference. Supersedes the separate S3 planning note.  
> Purpose: keep Asset Gate boundaries and next slices in one short file.

## 0. Decision

Asset Gate is the next core judge-side capability. It answers:

1. Are the available assets enough for a trustworthy review?
2. Should the reviewer consider unit, api, integration, or manual-oracle-first?

It is advisory only. It never changes `review_recommendation`, `conclusion`, `trusted`,
quality-gate status, aggregate headlines, or ledger badcase signatures.

## 1. Current State

Implemented:

- `review_summary["asset_sufficiency"]`
- digest flags for high/medium/low asset risks
- tiny `bundle["asset_facts"]` persisted by both generation and submit pipelines
- compact benchmark carry fields on `BenchCaseResult`
- compact ledger carry fields on `JudgedRecord`
- descriptive benchmark/ledger breakdown helpers
- benchmark markdown presentation for RAW and HEADLINE(real-only) Asset Gate breakdowns
- formal Test-Level Router boundary, report-only
- S4 audit and S4A report-only implementation design
- S4A report-only implementation completed; no executor, benchmark carry, or ledger carry
- producer-agnostic behavior for generated and submitted candidates

Files:

```text
app/quality/asset_sufficiency.py
app/quality/test_level_router.py
app/report/generation_report.py
app/review/review_digest.py
app/pipeline/generate_pipeline.py
app/pipeline/submit_pipeline.py
app/benchmark/models.py
app/benchmark/runner.py
app/benchmark/report_md.py
app/ledger/models.py
app/ledger/ingest.py
app/ledger/analytics.py
tests/test_asset_sufficiency.py
tests/test_test_level_router.py
tests/test_generation_report.py
tests/test_review_digest.py
tests/test_generate_pipeline.py
tests/test_submit_candidate.py
tests/test_benchmark.py
tests/test_ledger.py
```

Latest validation:

```text
41 passed
71 passed, 1 warning
62 passed
123 passed, 1 warning
427 passed, 4 skipped, 1 warning
```

## 2. Output Shape

```text
{
  "code_context": "sufficient|partial|missing",
  "existing_tests": "sufficient|partial|missing",
  "business_oracle": "sufficient|partial|missing",
  "test_data": "sufficient|partial|missing",
  "api_schema": "sufficient|partial|missing",
  "db_schema": "sufficient|partial|missing",
  "external_dependency_mock": "sufficient|partial|missing",
  "test_level_recommendation": "unit|api|integration|manual_oracle_first",
  "missing_assets": [],
  "risk_notes": [],
  "evidence": [],
  "advisory": true
}
```

Persisted `asset_facts` contains only small facts:

```text
neighbor_test_found
neighbor_test_methods
dependency_artifacts
build_java_source
target_has_method_source
target_method_specified
target_fields
target_constructors
target_methods
```

Never persist full `ContextSnapshot`, source excerpts, schema dumps, or model-declared claims as
trusted facts.

## 3. S2 Noise Rule

Dependency artifacts are corroborating evidence only.

Allowed:

```text
candidate source mentions JdbcTemplate + dependency_artifacts includes postgresql
  -> db_schema partial, integration recommendation

target simple name is UserController + dependency_artifacts includes spring-webmvc
  -> api_schema partial, api recommendation
```

Rejected:

```text
dependency_artifacts includes spring-webmvc/postgresql by itself
  -> no asset risk, keep unit recommendation
```

This prevents ordinary Spring/Maven projects from being marked API or integration candidates just
because the project POM has common dependencies.

## 4. S3A Benchmark Carry - Done

Benchmark carry fields:

```text
BenchCaseResult.asset_test_level_recommendation
BenchCaseResult.asset_missing_count
BenchCaseResult.asset_partial_count
```

These are populated in `runner._completed_result(...)` from
`review_summary["asset_sufficiency"]`. The runner does not compute new Asset Gate logic; it only
projects report facts.

S3A did not change:

- `aggregate(...)`
- `report_md`
- ledger models
- ledger analytics
- badcase signatures
- verdict/recommendation/conclusion/trusted

## 5. S3B Ledger Carry - Done

Ledger carry fields:

```text
JudgedRecord.asset_test_level_recommendation
JudgedRecord.asset_missing_count
JudgedRecord.asset_partial_count
```

These are copied in `record_from_bench_case(...)` from `BenchCaseResult`.

S3B did not change:

- SQLite indexed columns
- ledger analytics
- retrieval
- badcase signatures
- aggregate/report markdown
- verdict/recommendation/conclusion/trusted

## 6. S3C Descriptive Breakdown Helpers - Done

Benchmark helper:

```text
asset_gate_breakdown(cases, *, run_kind=None)
```

Ledger helper:

```text
asset_gate_summary(records, *, run_kind=None)
```

Both return descriptive counts:

```text
run_kind_filter
total / records
by_test_level
missing_asset_cases / missing_asset_records
partial_asset_cases / partial_asset_records
missing_assets_total
partial_assets_total
```

S3C did not change:

- aggregate headline keys
- report markdown
- SQLite indexed columns
- ledger retrieval
- badcase signatures
- verdict/recommendation/conclusion/trusted

## 7. S3D Markdown Presentation - Done

Decision: benchmark markdown should render Asset Gate breakdowns because this is the report-facing
evidence surface for comparing candidate reviewability across producers.

Rendering contract:

```text
Asset Gate - RAW (all run_kinds)
Asset Gate - HEADLINE (real only)
```

Each section should show only descriptive counts from `asset_gate_breakdown(...)`:

```text
total
run_kind_filter
by_test_level
missing_asset_cases
partial_asset_cases
missing_assets_total
partial_assets_total
```

Rules:

- keep the sections separate from `Aggregate` headlines;
- recompute the HEADLINE section with `run_kind="real"`;
- do not add Asset Gate keys to `aggregate(...)`;
- do not change per-case table columns in this slice;
- do not change recommendations, conclusions, trust, ledger signatures, or SQLite indexes.

S3D is presentation only. It makes existing S3C facts visible in markdown reports.

Implementation:

- `render_markdown(...)` renders `Asset Gate - RAW (all run_kinds)`.
- `render_markdown(...)` renders `Asset Gate - HEADLINE (real only)`.
- both sections use `asset_gate_breakdown(...)`.
- fake/dryrun/smoke/external/historical unknown rows stay out of the real-only section.
- aggregate headline keys remain unchanged.

Focused test expectation:

```text
render_markdown(...) contains both Asset Gate sections,
real-only counts exclude fake/dryrun/smoke/external/unknown rows,
set(aggregate(cases).keys()) stays unchanged.
```

## 8. S3D Audit - Done

Audit result, 2026-07-04:

- `estimate_asset_sufficiency(...)` is advisory and pure. It reads report facts plus the tiny
  persisted `asset_facts` block; it does not read repos, call models, or change verdicts.
- generation and submit pipelines both persist the same small `asset_facts` shape before
  preflight rejection, so generated and submitted candidates use the same judge-side signal.
- `assemble_generation_report(...)` attaches Asset Gate after quality/oracle/mock signals and
  before digest construction. It does not feed `recommend_with_reasons(...)`.
- `review_digest` reads Asset Gate only as flags for human review. Digest output keeps
  `auto_accept_blocked=True` and `conclusion=NEED_HUMAN_REVIEW`.
- benchmark carry and ledger carry copy compact fields only. They do not recompute Asset Gate
  logic, add SQLite indexes, alter badcase signatures, or change retrieval.
- benchmark and ledger breakdown helpers are descriptive and compose with `run_kind`.
- markdown presentation renders RAW and HEADLINE(real-only) Asset Gate sections from
  `asset_gate_breakdown(...)`; it does not add Asset Gate keys to `aggregate(...)`.

Audit fix made in this pass:

- the benchmark markdown aggregate headline now explicitly says
  `fake/dryrun/smoke/external/unknown excluded`, matching the actual `run_kind="real"` filter.

No drift found:

- no auto-accept or auto-reject path;
- no `trusted=True` path introduced;
- no recommendation/conclusion mutation from Asset Gate;
- no API/integration executor;
- no schema discovery, RAG, dependency, network, or model call;
- no aggregate headline metric change;
- no ledger signature/index change.

Residual watch item:

- Asset Gate counts are compact report counters. S4A's router is report-only; any next design must
  keep it owner-gated and must not add execution without separate approval.

## 9. S4 Test-Level Router Boundary - Record

Decision: the Test-Level Router is a report-facing contract over Asset Gate facts. It is not an
executor, not a candidate-kind expansion, and not an API/integration harness.

Purpose:

1. Make the current Asset Gate recommendation explicit and reviewable.
2. Separate "this unit-test kernel can judge now" from "future level requires owner approval".
3. Prevent API/integration signals from quietly turning into scope expansion.

### 9.1 Inputs

Allowed inputs are already-produced judge facts:

```text
review_summary.asset_sufficiency
quality_gate
preflight
oracle_strength_estimate
mock_smells
coverage_delta
target_class / target_method
run_kind / producer_id as provenance only
```

Rules:

- producer metadata is never asset proof;
- model-declared claims are never trusted facts;
- the router must not read repositories, schemas, databases, services, or `.env`;
- the router must not call models, network services, Maven, PIT, or any API harness;
- historical rows without router output remain unknown and are not backfilled.

### 9.2 Output Contract

Minimum report-only shape:

```text
test_level_router = {
  "recommended_level": "unit|api|integration|manual_oracle_first|unknown",
  "current_kernel_support": "supported|future_gated|manual_review_required|unknown",
  "owner_gate_required": true|false,
  "report_only": true,
  "advisory": true,
  "reason_codes": [],
  "evidence": []
}
```

Semantics:

- `recommended_level` is copied from Asset Gate when present, otherwise `unknown`.
- `current_kernel_support="supported"` only means the current Java/Maven unit-test judge can run
  the candidate kind already in hand. It does not mean acceptance.
- `current_kernel_support="future_gated"` means the target appears to need a future API or
  integration candidate level. It does not launch that level.
- `current_kernel_support="manual_review_required"` means business oracle assets must be supplied
  by a human before executor expansion should be considered.
- `owner_gate_required=false` only for `unit`.
- `owner_gate_required=true` for `api`, `integration`, `manual_oracle_first`, and `unknown`.
- `report_only=true` in all S4 output.

### 9.3 Level Mapping

| Asset Gate level | Router support | Meaning in S4 |
|---|---|---|
| `unit` | `supported` | Keep using the current Java/Maven unit-test judge kernel. |
| `api` | `future_gated` | A future API candidate level may be appropriate, but needs owner-approved design first. |
| `integration` | `future_gated` | A future integration candidate level may be appropriate, but needs owner-approved design first. |
| `manual_oracle_first` | `manual_review_required` | Human-supplied oracle/specification assets are needed before more automation. |
| missing/unknown | `unknown` | Do not infer a level from producer claims or artifacts alone; any follow-up requires owner review. |

### 9.4 Report Surface

The first implementation, if approved later, should surface the router only under
`review_summary`:

```text
review_summary["test_level_router"]
```

Optional later carry fields, still descriptive:

```text
BenchCaseResult.router_recommended_level
JudgedRecord.router_recommended_level
```

Do not add router fields to `aggregate(...)`, SQLite indexed columns, badcase signatures, or
headline metrics in the first implementation.

### 9.5 Owner Gate

Owner approval is required before any of these:

- adding a new candidate kind;
- adding an API/integration executor;
- discovering schemas, DBs, fixtures, environments, or services;
- storing schema/database/service assets;
- changing benchmark headline metrics;
- using router output to skip, fail, accept, reject, merge, or warehouse a candidate.

### 9.6 Non-Goals

The router does not:

- execute anything;
- decide acceptance or rejection;
- rewrite a candidate;
- select or call a producer;
- build a general API automation framework;
- build an environment/data orchestration layer;
- make API/integration rows part of real-model unit-test headlines.

### 9.7 Acceptance For A Future Code Slice

If S4 is implemented later, focused tests must prove:

- `review_summary["test_level_router"]` is present and advisory;
- unit maps to `supported`, api/integration map to `future_gated`, manual maps to
  `manual_review_required`;
- `conclusion` remains `NEED_HUMAN_REVIEW` and `trusted` remains `False`;
- `review_recommendation`, `aggregate(...)` keys, badcase signatures, and SQLite indexes are
  unchanged;
- run_kind filtering still excludes fake/dryrun/smoke/external/unknown from real-only headlines;
- no repo reads, model calls, network calls, or new dependencies are introduced.

## 10. S4 Audit - Done

Audit result, 2026-07-04:

- S4 stays within the Asset Gate pillar. It clarifies the test-level recommendation already emitted
  by `review_summary["asset_sufficiency"]`.
- The current report assembler has all S4A inputs in one place after Asset Gate and before digest,
  so a future implementation does not need runner, ledger, benchmark, schema, DB, or executor
  changes.
- The router should not be a digest flag in the first code slice. Digest already surfaces the
  underlying Asset Gate risks; adding router flags now would duplicate severity and could look like
  a new verdict.
- The router must not read repos, schemas, databases, services, `.env`, Maven output, PIT output,
  network, or models.
- The router must not alter `review_recommendation`, `conclusion`, `trusted`, quality-gate status,
  aggregate headlines, SQLite indexes, ledger signatures, or benchmark markdown.
- `unknown` is not a safe auto-path. It should require owner review before any future non-unit
  action.

No drift found:

- no executor path;
- no candidate-kind expansion;
- no API/integration harness;
- no producer self-certification;
- no auto-accept or auto-reject.

## 11. S4A Report-Only Implementation - Live

S4A is the smallest code slice allowed after this design audit. It is now implemented as a
report-only field and remains non-executing.

### 11.1 Scope

Allowed:

- add one pure helper, for example `app/quality/test_level_router.py`;
- attach its output to `review_summary["test_level_router"]` in `assemble_generation_report(...)`;
- build it after `asset_sufficiency` and before `digest`;
- add focused offline tests.

Not allowed:

- no benchmark carry fields;
- no ledger fields;
- no SQLite columns or indexes;
- no markdown section;
- no digest flags;
- no executor, candidate kind, schema discovery, DB discovery, service discovery, or API harness.

### 11.2 Pure Helper Contract

Suggested function shape:

```text
route_test_level(
  *,
  asset_sufficiency: dict | None,
  run_kind: str | None = None,
  producer_id: str | None = None
) -> dict
```

The helper reads only the passed dicts/strings. It never inspects source code, files, network,
environment, dependency graphs, or producer claims.

Output:

```text
{
  "recommended_level": "unit|api|integration|manual_oracle_first|unknown",
  "current_kernel_support": "supported|future_gated|manual_review_required|unknown",
  "owner_gate_required": true|false,
  "report_only": true,
  "advisory": true,
  "reason_codes": [],
  "evidence": [],
  "note": "test-level routing is advisory and launches no executor"
}
```

Mapping:

```text
unit                -> supported, owner_gate_required=false
api                 -> future_gated, owner_gate_required=true
integration         -> future_gated, owner_gate_required=true
manual_oracle_first -> manual_review_required, owner_gate_required=true
missing/unknown     -> unknown, owner_gate_required=true
```

Suggested reason codes:

```text
asset_level_unit
asset_level_api_future_gated
asset_level_integration_future_gated
asset_level_manual_oracle_first
asset_level_unknown
provenance_is_context_not_proof
```

Evidence should be compact and non-source:

```text
{"source": "asset_sufficiency", "field": "test_level_recommendation", "value": "..."}
{"source": "provenance", "run_kind": "...", "producer_id_present": true}
```

Do not copy source excerpts, schema data, environment data, or model-declared asset claims.

### 11.3 Report Wiring

In `assemble_generation_report(...)`:

```text
review_summary["asset_sufficiency"] = estimate_asset_sufficiency(...)
review_summary["test_level_router"] = route_test_level(
    asset_sufficiency=review_summary["asset_sufficiency"],
    run_kind=generation.get("run_kind"),
    producer_id=result.get("producer_id") or generation.get("producer_id"),
)
review_summary["digest"] = build_review_digest(review_summary)
```

The router output is visible to the human reviewer, but the digest should ignore it in S4A.

### 11.4 S4A Tests

Focused tests should prove:

- pure helper maps `unit`, `api`, `integration`, `manual_oracle_first`, and missing/unknown exactly
  as specified;
- helper output always has `report_only=true` and `advisory=true`;
- provenance appears only as context evidence, never as asset proof;
- `assemble_generation_report(...)` attaches `review_summary["test_level_router"]`;
- `review_recommendation`, `conclusion`, `trusted`, quality-gate status, digest standing facts,
  aggregate keys, badcase signatures, SQLite schema, benchmark markdown, and ledger models remain
  unchanged;
- no model/network calls, repo reads, `.env` reads, new dependencies, or executor calls are added.

Suggested focused commands:

```powershell
& "E:\AI-Test-Platform\.venv\Scripts\python.exe" -m pytest tests/test_test_level_router.py tests/test_generation_report.py tests/test_review_digest.py
& "E:\AI-Test-Platform\.venv\Scripts\python.exe" -m pytest tests/test_benchmark.py tests/test_ledger.py tests/test_submit_candidate.py tests/test_submit_candidate_s2.py
```

Then run the full suite with the project venv.

## 12. S4A Design Audit - Done

Audit result, 2026-07-04:

- S4A remains report-only if it is implemented exactly as one pure helper plus
  `review_summary["test_level_router"]` wiring.
- `assemble_generation_report(...)` is the correct and only first wiring point because it already
  has `asset_sufficiency`, `run_kind`, and `producer_id` in memory.
- The helper must consume only explicit parameters. It must not import repo/context collectors,
  Maven/PIT helpers, API clients, ledger, benchmark runner, settings, or environment access.
- Digest must ignore `test_level_router` in S4A. Asset Gate already contributes digest flags; adding
  router flags would duplicate severity and make routing look like a verdict.
- Benchmark carry, ledger carry, markdown presentation, aggregate keys, SQLite schema, and badcase
  signatures must remain unchanged in S4A.
- Provenance may appear only as compact context evidence. It must not affect
  `recommended_level`, `current_kernel_support`, or `owner_gate_required`.
- `unknown` remains owner-gated. Missing Asset Gate output must not silently become `unit`.

No drift found in the design:

- no executor path;
- no candidate-kind expansion;
- no API/integration harness;
- no new dependency or model/network call;
- no route-to-accept/reject behavior;
- no headline metric or ledger-signature change.

Implementation status:

- Implemented on 2026-07-04 as one pure helper plus
  `review_summary["test_level_router"]` wiring.
- Focused evidence: `41 passed`; benchmark/ledger/submit focused evidence:
  `71 passed, 1 warning`.
- Still requires a fresh owner-approved design before any executor, candidate-kind,
  benchmark carry, ledger carry, markdown section, or digest flag is added.

## 13. Carry Field Semantics

Fields on `BenchCaseResult` and `JudgedRecord`:

```text
asset_test_level_recommendation: str | None = None
asset_missing_count: int = 0
asset_partial_count: int = 0
```

Meanings:

- `asset_test_level_recommendation`: copied from
  `review_summary["asset_sufficiency"]["test_level_recommendation"]`.
- `asset_missing_count`: count of `missing_assets`.
- `asset_partial_count`: count of real partial asset notes.

Partial count must ignore the report-local `existing_tests` placeholder:

```text
{"asset": "existing_tests", "status": "partial",
 "reason": "report-local S1 does not persist neighbor-test asset facts"}
```

Reason: this placeholder means "older report shape lacked S2 facts", not that the candidate
actually has a review asset gap. In normal S2 pipeline runs, `asset_facts` exists and this
placeholder should not appear.

### 13.1 Runner Wiring

In `_completed_result(...)`, compute once:

```text
review_summary = _review_summary_with_rubric(rep.get("review_summary"), case)
asset = (review_summary or {}).get("asset_sufficiency") or {}
```

Then populate the new `BenchCaseResult` fields from `asset`.

Do not compute new Asset Gate logic in `runner.py`. The runner only projects report facts.

### 13.2 Ledger Wiring

In `record_from_bench_case(...)`, copy the three compact fields from `BenchCaseResult` to
`JudgedRecord`. Do not index them in SQLite in this slice; they round-trip through `record_json`.

### 13.3 Failure Paths

Setup failures and baseline failures should keep defaults:

```text
asset_test_level_recommendation = None
asset_missing_count = 0
asset_partial_count = 0
```

For generation failures that still produce a report, carry whatever
`assemble_generation_report(...)` emits.

### 13.4 Tests

Current focused tests:

```text
test_completed_result_carries_compact_asset_gate_fields_without_aggregate_change
test_record_from_bench_case_carries_asset_gate_fields_without_changing_signature
test_asset_gate_breakdown_composes_with_run_kind_without_headline_change
test_asset_gate_summary_composes_with_run_kind_and_preserves_signatures
test_render_markdown_includes_asset_gate_breakdown_without_headline_drift
```

They assert:

- benchmark and ledger rows copy compact fields.
- the S1 `existing_tests` placeholder is not counted as a real partial asset in benchmark carry.
- `set(aggregate([...]).keys())` is unchanged by the new per-case fields.
- ledger target/author/fingerprint queries still work.
- badcase signature ignores Asset Gate fields.
- `conclusion` remains `NEED_HUMAN_REVIEW`.

Focused command:

```powershell
& "E:\AI-Test-Platform\.venv\Scripts\python.exe" -m pytest tests/test_benchmark.py tests/test_ledger.py tests/test_run_kind.py tests/test_oracle_strength.py tests/test_business_tags.py
```

Then run the full suite with the project venv.

## 14. Non-Goals

Do not:

- build a Test-Level Router executor;
- launch API/integration harnesses;
- add candidate kinds;
- add schema/database discovery;
- add RAG, embeddings, new dependencies, or model calls;
- read `.env`;
- use producer metadata as asset proof;
- treat Asset Gate as accept/reject.

## 15. Next Prompt

```text
Audit the S4A report-only Test-Level Router implementation before considering any next slice.

Read:
- docs/00_foundation/54_CORE_FREEZE_AND_BOUNDARY_REFERENCE.md
- docs/50_benchmark/55_ASSET_GATE_NEXT_STEP_AUDIT.md
- app/quality/asset_sufficiency.py
- app/report/generation_report.py
- app/benchmark/report_md.py
- app/pipeline/generate_pipeline.py
- app/pipeline/submit_pipeline.py

Task:
S4A report-only implementation is live. Audit that it remains exactly one pure helper plus
`review_summary["test_level_router"]` wiring described in sections 11 and 12. Do not add benchmark
carry, ledger carry, markdown sections, digest flags, candidate kinds, or API/integration
execution.

Tests:
Keep focused tests proving the router is advisory, report-only, maps levels correctly, treats
provenance as context only, and does not change verdict/recommendation/conclusion/trusted,
aggregate headline keys, SQLite indexes, badcase signatures, digest standing facts, benchmark
markdown, or ledger models. Run focused tests and full pytest with the project venv.

Red lines:
No aggregate headline changes. No badcase signature changes. No model/network calls. No new
dependencies. No executor/router automation yet. No verdict/recommendation/conclusion/trusted
changes.
```

## 16. Post-S4A Design Queue

After the S4A report-only router audit passes, keep the next designs evidence-governance-first:

```text
S5B Golden Set governance
  Clarify benchmark-manifest case roles, stability rules, risk coverage, and admission criteria.
  No model run, no runner change, no historical DB backfill in the first design slice.

S5C Badcase RCA taxonomy
  Stabilize human-declared root_cause / fix_note language for grouping and retrieval.
  Do not auto-fill RCA fields and do not change badcase signatures in the first design slice.

S5D Skill/SOP templates
  Describe safe judge workflows: trigger, inputs, steps, evidence, red lines, output, fallback.
  Do not create a broad skill platform or prompt-based evaluator.

S5E LLM Judge calibration
  Future-gated only. Requires human calibration set, confidence/reason/evidence output, bias
  controls, and advisory-only report placement.
```

The design queue comes from `docs/knowledge/AGENT_HARNESS_EVALUATION_KB.md`. Treat it as a queue
of owner-gated design options, not as approval to implement.
