# Work Log - Current Snapshot

> Refreshed: 2026-07-04
> Purpose: one short handoff file. Read this first, then `docs/README.md`, `54`, and `55`.

## 1. Product Thesis

TestAgent Lab is an execution-based judge for test candidates from any producer.

It does not claim that generated tests are valuable. A candidate only becomes reviewable after:

```text
compile -> execute -> quality gate -> advisory signals -> review digest -> report
```

The final conclusion remains:

```text
conclusion = NEED_HUMAN_REVIEW
trusted = False
```

## 2. Current Architecture Map

Current runtime shape:

```text
Producer entries
  built-in generator -> app.pipeline.generate_pipeline.run_generation
  submit_candidate   -> app.pipeline.submit_pipeline.run_external_candidate
    -> common generation bundle

Judge kernel
  repo import / workspace
  -> target select
  -> bounded context + tiny asset_facts
  -> preflight
  -> write candidate test
  -> Maven/Surefire execution
  -> JaCoCo coverage delta

Report and signals
  app.report.generation_report.assemble_generation_report
    -> quality gate
    -> review policy
    -> oracle strength
    -> mock smell
    -> asset sufficiency
    -> test level router, report-only
    -> review digest
    -> conclusion = NEED_HUMAN_REVIEW, trusted = False

Comparison and memory
  benchmark runner -> BenchCaseResult / BenchReport -> run_kind-filtered aggregates
  ledger ingest    -> JudgedRecord -> analytics / retrieval
```

Module boundaries:

- `app/pipeline/` orchestrates flows and persists job bundles; it should not own quality logic.
- `app/report/` shapes evidence into the review report; it should not execute Maven, mutate repos,
  or write ledger records.
- `app/quality/` owns pure advisory signal helpers; they should not read `.env`, call models,
  write DB rows, or change verdicts.
- `app/review/` owns recommendation and digest roll-up; digest reads existing signals and does not
  become a new detector.
- `app/benchmark/` compares judged cases and projects compact facts; headline views must filter
  `run_kind="real"`.
- `app/ledger/` stores and retrieves judged records; precipitation is best-effort and must not
  change benchmark outcomes.
- `app/llm/`, `app/generate/`, `app/repair/`, and prompt/context tuning are producer-side support,
  not product center.

Architecture invariants:

- Every producer enters the same judge/report path.
- Provenance is context, never quality proof.
- Asset Gate and Test-Level Router are advisory; S4A is report-only and launches no executor.
- Benchmark/ledger carry fields are compact projections, not new scoring systems.
- No layer may auto-accept, auto-merge, or turn `trusted` true.

## 3. Current Core Boundary

Freeze and protect:

- Repo Import / Maven Judge / Surefire / JaCoCo
- Candidate Submit
- Quality Gate
- Preflight
- Mutation, gated off by default
- Invariant Review
- Mock Smell
- Badcase Ledger
- Review Digest
- Benchmark Manifest
- Report

Downgraded producer-side support:

- LLM Client
- Prompt Builder
- Platform Generator
- Compile Repair
- Context Prompt Tuning

Rejected mainline:

- prompt pile-up
- generated pass-rate race
- multi-provider platform
- complex RAG
- large MCP or web backend
- automatic adoption / auto-merge / auto-warehouse entry

## 4. Current Asset Gate State

Implemented:

- `review_summary["asset_sufficiency"]`
- digest flags for Asset Gate findings
- tiny `bundle["asset_facts"]` persisted by both generation and submit pipelines
- compact benchmark carry fields on `BenchCaseResult`
- compact ledger carry fields on `JudgedRecord`
- descriptive benchmark/ledger breakdown helpers
- benchmark markdown Asset Gate RAW and HEADLINE(real-only) sections
- S3D audit completed; real-only benchmark headline explicitly excludes `external`
- S4 Test-Level Router boundary designed as report-only and owner-gated
- S4 audit completed; S4A report-only implementation design drafted
- S4A report-only Test-Level Router implemented as report field only
- S2 noise rule: dependency artifacts corroborate source/target hints; they do not trigger
  API/integration risks by themselves

Important files:

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
docs/50_benchmark/55_ASSET_GATE_NEXT_STEP_AUDIT.md
```

Latest validation:

```text
41 passed
71 passed, 1 warning
62 passed
123 passed, 1 warning
427 passed, 4 skipped, 1 warning
```

## 5. Next Approved-Shape Slice

Next work should be audit-first, not automatic expansion:

```text
Audit S4A report-only Test-Level Router implementation before any next slice
```

S4A is live only as a report field: one pure helper plus
`review_summary["test_level_router"]` wiring. "Continue" alone is not approval to add execution,
benchmark carry, ledger carry, markdown sections, digest flags, or candidate kinds.

Do not change:

- aggregate headline metrics
- SQLite indexes
- badcase signatures
- verdict, recommendation, conclusion, or trusted status
- candidate kinds or API/integration executors
- digest severity/flags

## 6. Read Rules

Default read set:

```text
docs/README.md
docs/00_foundation/00_PROJECT_CHARTER.md
docs/00_foundation/40_CORE_THESIS_REPOSITIONING.md
docs/00_foundation/54_CORE_FREEZE_AND_BOUNDARY_REFERENCE.md
docs/50_benchmark/55_ASSET_GATE_NEXT_STEP_AUDIT.md
```

Historical numbered docs are archive. Read them only when a task names them or an active doc
points to them.

## 7. Machine Rules

- Use venv Python: `E:\AI-Test-Platform\.venv\Scripts\python.exe`
- Do not read `.env`.
- Do not make real model/API calls without explicit approval.
- Push is human-only.
- Historical benchmark DBs are read-only; never backfill.
- Tests must not contact real LLM providers.
