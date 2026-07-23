# TestAgent Lab

Execution-based candidate evaluation for test-generating agents.

This project is not a test generator as the product. It is the judge layer:

```text
candidate -> compile/execute evidence -> quality signals -> review digest -> badcase ledger -> report
```

Generated tests, submitted tests, tool-produced tests, and human-written tests are all candidates.
A candidate is never accepted automatically. Reports keep:

```text
conclusion = NEED_HUMAN_REVIEW
trusted = False
```

## Current Shape

Core runtime:

- `app/pipeline/`: orchestrates generation and external candidate submission.
- `app/report/`: assembles evidence, advisory signals, API report-only facts, and final report.
- `app/quality/`: pure quality and asset-sufficiency helpers.
- `app/review/`: advisory recommendation and review digest.
- `app/benchmark/`: run_kind-aware benchmark aggregates and named projections.
- `app/ledger/`: judged-record storage, badcase analytics, and retrieval.
- `app/governance/`: pure design-time policy helpers for external asset phase gates, reuse-check
  plans, and knowledge embedding destinations.
- `app/api/`: HTTP entrypoints, including `submit_candidate`.

Current kernel:

- Java/Maven candidate execution through Maven/Surefire/JaCoCo; JUnit stays the thin
  compatibility path and TestNG is now report-visible.
- The built-in JUnit generator is a legacy failed exploration retained only as a removable
  producer/compatibility path, not as product direction.
- Producer-agnostic `submit_candidate`.
- Quality gate, preflight, oracle-strength estimate, invariant review, mock smell, review digest.
- Badcase ledger and retrieval.
- Human/golden label readiness and Golden Set defect-denominator readiness summaries for
  real-world validation metrics; still no headline outcome claim without labels/denominators.
- Asset Gate S1-S4A, including report-only Test-Level Router.
- Mandatory reuse-check governance for design inputs, with metadata-only validation and plan summary.
- Knowledge embedding destination routing for new external lessons/audits; still metadata-only.
- Evaluation Skill/SOP blueprint readiness for reusing judge workflows; still no installed Skill
  runtime.
- Advisory project progress snapshot: current weighted estimate is about 71%, not yet 80%.
- Landing-readiness rollup combines progress, supplied human/golden labels, and supplied Golden
  Set seed metadata into one planning view; still no release/headline/verdict authority.
- Optional landing-readiness Markdown rendering for human handoff; still no default report wiring
  or release authority.
- Landing-readiness review questions and evidence checklist for human audit; still no evidence
  collection, dataset/verifier approval, or headline authority.
- Landing-readiness snapshot validation before Markdown rendering, rejecting forged authority
  flags instead of displaying them as normal handoff material.
- Typed landing-readiness validation for percent, stage, source-version, input-count, metric-count,
  and nested progress consistency.
- Derived landing-readiness validation for blockers, next steps, input counts, denominator flags,
  review questions, and evidence-checklist status consistency.
- Landing-readiness blocker-family summary and Markdown table for human audit navigation; still no
  workspace scan, evidence collection, release gate, or headline authority.
- Landing-readiness blocker-summary validation for standalone handoff artifacts; still no source
  recompute, evidence collection, release gate, or headline authority.
- Optional landing-readiness blocker-summary Markdown rendering for standalone human handoff;
  still no source recompute, default report wiring, release gate, or headline authority.
- S6 landing-readiness governance is now frozen for normal progress work; next progress should
  come from one joint human-label + Golden Set evidence closure slice. API/interface
  implementation design is lower priority until that joint slice exposes a concrete need.
- CI/PR handoff now groups project-progress and human/golden metric readiness changes into a
  `landing_readiness_snapshots` review batch; still human-only staging/commit/push.
- Report-only Java test framework facts (`junit4`/`junit5`/`testng`/`mixed`/`unknown`) plus
  optional `submit_candidate` framework declaration carry, so enterprise TestNG candidates are
  visible without changing the runner.
- API/interface reuse-plan sample over active registry/matrix sources; still metadata-only.
- First P0 external README audit records for Schemathesis/Newman/WireMock; still no install,
  execution, service orchestration, or adapter.
- API/interface candidate path through report-only `junit_api_candidate` evidence, smoke manifest,
  denominator policy, benchmark projection, markdown display, compact ledger JSON carry, and pure
  ledger projection helper with conditional presentation and cross-layer projection boundary tests.

Not built without explicit approval:

- API/interface executor.
- New live candidate kinds beyond the report-only path.
- Existing API smoke ledger analytics changes, retrieval scoring, or signature changes.
- External database connections, benchmark/dataset downloads, external SUT import, open-source
  tool execution/vendoring, Docker/service orchestration, model calls, auto-repair/adoption,
  auto-merge.

## Read First

Use the thin context layer before opening deeper docs:

```text
docs/WORK_LOG.md
docs/README.md
docs/00_foundation/54_CORE_FREEZE_AND_BOUNDARY_REFERENCE.md
docs/knowledge/README.md
docs/knowledge/EXTERNAL_ASSET_MAPPING_MATRIX.md
docs/knowledge/EXTERNAL_ASSET_PHASE_PLAN.md
```

The active doc index is [docs/README.md](docs/README.md).
The current docs and architecture audit is
[docs/00_foundation/61_CURRENT_DOCS_AND_ARCHITECTURE_AUDIT.md](docs/00_foundation/61_CURRENT_DOCS_AND_ARCHITECTURE_AUDIT.md).

## Verify

Use the project venv. Bare `python` may be the Windows Store stub on this machine.

```powershell
& "E:\AI-Test-Platform\.venv\Scripts\python.exe" -m pytest
```

Recent evidence:

```text
747 passed, 4 skipped, 1 warning in 6.92s
```

## Guardrails

- Never read, print, summarize, or commit `.env`.
- No real model/API calls without explicit approval and cost disclosure.
- No auto-accept, auto-merge, or `trusted=True`.
- No headline metrics over fake/dryrun/smoke/external/historical unknown rows.
- No external asset execution, dataset download, external DB connection, code vendoring, or new
  dependency without an owner-approved design.
- Do not let legacy JUnit generation work drive roadmap priority; judge/harness evidence is the
  product center.
