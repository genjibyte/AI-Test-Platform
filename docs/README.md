# TestAgent Lab Docs

> Goal: reduce doc-driven hallucination. Read the active set first; treat old numbered files as
> archive unless a task explicitly names them.

## Active Read Set

Read these for normal design or implementation work:

- [WORK_LOG.md](/docs/WORK_LOG.md) - current snapshot and next step
- [00 Project Charter](/docs/00_foundation/00_PROJECT_CHARTER.md) - binding constraints
- [40 Core Thesis Repositioning](/docs/00_foundation/40_CORE_THESIS_REPOSITIONING.md) - product thesis
- [42 AI Test Failure Empirical Audit](/docs/00_foundation/42_AI_TEST_FAILURE_EMPIRICAL_AUDIT.md) - evidence discipline
- [54 Core Freeze And Boundary Reference](/docs/00_foundation/54_CORE_FREEZE_AND_BOUNDARY_REFERENCE.md) - current boundary
- [55 Asset Gate Design Digest](/docs/50_benchmark/55_ASSET_GATE_NEXT_STEP_AUDIT.md) - current Asset Gate plan
- [Knowledge Index](/docs/knowledge/README.md) - external knowledge entrypoint

## Current Thesis

TestAgent Lab is an execution-based judge for test candidates from any producer.

The canonical current architecture map is `WORK_LOG.md` section 2. Treat it as the first
module-boundary reference before opening older numbered design records.

```text
Candidate
  -> Maven/Surefire/JaCoCo evidence
  -> quality/value signals
  -> review digest
  -> badcase ledger
  -> reproducible report
  -> conclusion = NEED_HUMAN_REVIEW
```

Generation is only one producer. Do not optimize the project around prompt quality or generated
pass rate.

## Active Signals

The current value-judgment layer is advisory:

- `43` run_kind hygiene
- `45` business-invariant tags
- `46` oracle strength and gated mutation
- `48` invariant review
- `49` survived-mutant classification
- `50` badcase retrieval
- `51` mock smell
- `52` review digest
- `53` submit_candidate
- `55` Asset Gate: S1-S3D live; S4A Test-Level Router is report-only live, no executor

None of these auto-accepts a candidate.

## Archive Policy

Most numbered docs are historical design records. They are useful for archaeology, but should not
be treated as the latest plan unless `WORK_LOG.md`, `54`, or `55` points to them.

Existing consolidated digests:

- [Context v3 Evolution Digest](/docs/60_context_v3/CONTEXT_V3_EVOLUTION_DIGEST.md)
- [Preflight Evolution Digest](/docs/70_preflight/PREFLIGHT_EVOLUTION_DIGEST.md)

Historical folders:

- `docs/10_phase1`
- `docs/20_phase2`
- `docs/30_phase2_5_quality`
- `docs/40_phase3_phase4`
- detailed signal designs under `docs/50_benchmark`

## Red Lines

- Never read, print, summarize, or commit `.env`.
- No real model/API calls without explicit user approval and cost disclosure.
- No auto-accept: `conclusion` stays `NEED_HUMAN_REVIEW`, `trusted=False`.
- No headline metrics over fake/dryrun/smoke/external/historical unknown rows.
- No new dependencies or broad architecture changes without explicit approval.
