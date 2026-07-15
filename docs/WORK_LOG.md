# Work Log - Current Snapshot

> Refreshed: 2026-07-10
> Purpose: one short handoff file. Read this first, then route to the few docs needed for the
> task. Do not turn the knowledge base into a default read pile.

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
430 passed, 4 skipped, 1 warning
435 passed, 4 skipped, 1 warning
```

## 5. Next Design Queue

Next work should keep the product mainline open beyond Java/Maven unit tests: toward
producer-agnostic API/interface candidate evaluation and automated-test-generation outputs as
candidate inputs. Do a bounded S4A audit, then prefer S6 boundary design over more prompt,
generator, or pass-rate tuning unless that work fixes a concrete evidence/red-line issue.
Governance and external-asset work are support tracks, not blockers for the mainline.

```text
S5A   Closeout audit: S4A report-only Test-Level Router stays advisory and non-executing
S6A   Drafted: API/interface Candidate boundary from Minimal Judge Contract
S6A1  Live: pure JudgeEvidence projection for current Java/Maven report facts
      (`app/report/judge_evidence.py`, `tests/test_judge_evidence.py`)
S6B   Drafted: compact API report contract from JudgeEvidence fields
      (`docs/60_api_candidate/03_API_COMPACT_REPORT_CONTRACT.md`)
S6C   Live V1: selected `junit_api_candidate` as the minimal S7 smoke path
      and added pure API evidence block validation; still no executor
      (`docs/60_api_candidate/04_S7_SMOKE_PATH_SELECTION.md`,
      `app/report/api_evidence.py`, `tests/test_api_evidence.py`)
S7A   Live V1: report-only `api_evidence` wiring for `junit_api_candidate`
      (`docs/60_api_candidate/05_S7A_JUNIT_API_REPORT_ONLY_WIRING_DESIGN.md`,
      `app/report/generation_report.py`, `tests/test_generation_report_api_evidence.py`)
S7B   Drafted: submit_candidate report-only extension for `candidate_kind` and
      compact `api_evidence`
      (`docs/60_api_candidate/06_S7B_SUBMIT_API_REPORT_ONLY_EXTENSION_DESIGN.md`)
S7C   Drafted: `junit_api_candidate` smoke manifest / exam-bag contract
      (`docs/60_api_candidate/07_S7C_JUNIT_API_SMOKE_MANIFEST_DESIGN.md`)

Support tracks, only when needed:
S5B0  Run P0 external asset README audit from docs/knowledge/EXTERNAL_ASSET_MAPPING_MATRIX.md
S5B   Design Golden Set / benchmark-manifest governance
S5B1  Live V1: real-world validation automated evidence line
      (`docs/50_benchmark/56_REAL_WORLD_VALIDATION_LINE.md`,
      `app/benchmark/validation_line.py`, `tests/test_validation_line.py`)
S5C   Live V1: human review and RCA label pure validator
      (`docs/50_benchmark/57_HUMAN_REVIEW_RCA_LABEL_CONTRACT.md`,
      `app/review/human_labels.py`, `tests/test_human_labels.py`)
S5D   Design Skill/SOP templates for using the judge safely
S5E   Design optional LLM Judge calibration only if explicitly approved
```

S4A is live only as a report field: one pure helper plus
`review_summary["test_level_router"]` wiring. "Continue" alone is not approval to add execution,
benchmark carry, ledger carry, markdown sections, digest flags, or candidate kinds.

The next design should strengthen the same judge kernel across candidate levels, not generation
pass rate:

- API/interface work starts as a candidate/evidence/report contract, not an API automation
  framework.
- API/interface candidate evaluation should not be treated as a distant optional topic. It is the
  preferred next design direction once S4A report-only invariants are checked.
- S7C smoke work should pin a concrete manifest denominator and asset requirements before any
  executor, dependency, external SUT import, or benchmark/ledger carry.
- Real-world validation metrics must separate automated evidence from human/golden labels; do not
  headline usable-test rate, defect discovery, diagnosis time, or misjudgment rate before their
  required labels exist.
- Golden Set work belongs to benchmark manifest governance, not new model runs.
- External asset work starts with README/design audit, not vendoring or installing tools.
- RCA work guides human-declared root causes; it must not fabricate root cause.
- Skill/SOP work describes safe workflows; it must not create a new platform surface.
- LLM Judge remains future gated and advisory only.

Do not change:

- aggregate headline metrics
- SQLite indexes
- badcase signatures
- verdict, recommendation, conclusion, or trusted status
- candidate kinds or API/integration executors
- digest severity/flags

## 6. Three-Layer Read Rules

Follow the canonical mechanism in `docs/README.md`. For quick handoff, the Layer 1 thin set is:

```text
docs/WORK_LOG.md
docs/README.md
docs/00_foundation/54_CORE_FREEZE_AND_BOUNDARY_REFERENCE.md
docs/knowledge/README.md
docs/knowledge/EXTERNAL_ASSET_MAPPING_MATRIX.md
```

This is the required read set for every design. It is intentionally small: do not read all
numbered docs or all knowledge packs unless the task routes to them.

Layer 2 routes by need:

```text
API/interface -> docs/40 §10 + docs/60_api_candidate/00 + docs/60_api_candidate/01 + docs/60_api_candidate/02
API smoke     -> docs/60_api_candidate/03 + docs/60_api_candidate/04 + docs/60_api_candidate/05 + docs/60_api_candidate/06 + docs/60_api_candidate/07
Asset Gate    -> docs/50_benchmark/55
Metrics       -> docs/42 + docs/50_benchmark/43 + docs/50_benchmark/56
Human labels  -> docs/50_benchmark/56 + docs/50_benchmark/57
External asset-> docs/knowledge/EXTERNAL_ASSET_MAPPING_MATRIX.md, then README audit if needed
Knowledge     -> docs/knowledge/README.md, then only the named knowledge file
```

Layer 3 is only for proof, implementation detail, or archaeology: code/tests for touched modules,
large knowledge packs, historical numbered docs, external repo audits, benchmark reports, or
ledger records. Read them only when Layer 2 proves they are needed.

External asset rule:

```text
asset -> intake shape -> project artifact -> evidence -> red lines
```

Never stop at "useful". Use `EXTERNAL_ASSET_MAPPING_MATRIX.md` to choose one of:
`knowledge_note`, `readme_audit`, `manifest_seed`, `dataset_slice`, `producer_adapter`,
`executor_adapter`, `sut_target`, `isolation_support`, `provenance_support`, `discovery_index`,
`support_only`, or `reject_mainline`.

## 7. Machine Rules

- Use venv Python: `E:\AI-Test-Platform\.venv\Scripts\python.exe`
- Do not read `.env`.
- Do not make real model/API calls without explicit approval.
- Push is human-only.
- Historical benchmark DBs are read-only; never backfill.
- Tests must not contact real LLM providers.
