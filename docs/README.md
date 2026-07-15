# TestAgent Lab Docs

> Goal: reduce doc-driven hallucination. Read the active set first; treat old numbered files as
> archive unless a task explicitly names them.

## Three-Layer Read Mechanism

Every design should use three layers. The goal is to read enough to stay correct, without loading
the whole docs tree.

### Layer 1 - Thin Required Read

Read these every design session:

```text
docs/WORK_LOG.md
docs/README.md
docs/00_foundation/54_CORE_FREEZE_AND_BOUNDARY_REFERENCE.md
docs/knowledge/README.md
docs/knowledge/EXTERNAL_ASSET_MAPPING_MATRIX.md
```

Layer 1 answers current state, boundary, next direction, external-asset mapping, and which extra
docs are allowed for the current task.

### Layer 2 - Task-Routed Read

Read only the docs needed by the active design need:

| Task | Read additionally |
|---|---|
| API/interface candidate mainline | Preferred next direction after S4A closeout: [40 Core Thesis Repositioning §10](/docs/00_foundation/40_CORE_THESIS_REPOSITIONING.md), [API Candidate Judge Boundary](/docs/60_api_candidate/00_API_CANDIDATE_JUDGE_BOUNDARY.md), [Minimal Judge Contract](/docs/60_api_candidate/01_MINIMAL_JUDGE_CONTRACT.md), [API Candidate Boundary Design](/docs/60_api_candidate/02_API_CANDIDATE_BOUNDARY_DESIGN.md) |
| Asset Gate / Test-Level Router | [55 Asset Gate Design Digest](/docs/50_benchmark/55_ASSET_GATE_NEXT_STEP_AUDIT.md) |
| Benchmark metrics or historical data | [42 AI Test Failure Empirical Audit](/docs/00_foundation/42_AI_TEST_FAILURE_EMPIRICAL_AUDIT.md), `docs/50_benchmark/43_RUN_KIND_DESIGN.md` |
| External assets or repo intake | [External Asset Mapping Matrix](/docs/knowledge/EXTERNAL_ASSET_MAPPING_MATRIX.md), then a focused README audit when the matrix calls for it |
| External lessons / skills / harness patterns | [Knowledge Index](/docs/knowledge/README.md), then only the named knowledge file |

For real-world landing metrics, also read
`docs/50_benchmark/56_REAL_WORLD_VALIDATION_LINE.md`. This is the metric contract for first
compile pass, first test pass, usable-test rate, weak assertion detection, defect discovery, human
edit count, human handling time, diagnosis time, and misjudgment rate.

For human-review labels, RCA, usable-test rate, diagnosis time, or misjudgment-rate design, also
read `docs/50_benchmark/57_HUMAN_REVIEW_RCA_LABEL_CONTRACT.md`.

For API/interface candidate mainline work, also read
`docs/60_api_candidate/03_API_COMPACT_REPORT_CONTRACT.md` once the task reaches report evidence,
S6B, S6C, or S7 smoke-path design. For smoke-path choice, API evidence validation, or S7
implementation planning, also read `docs/60_api_candidate/04_S7_SMOKE_PATH_SELECTION.md`. For
`junit_api_candidate` report-only wiring, also read
`docs/60_api_candidate/05_S7A_JUNIT_API_REPORT_ONLY_WIRING_DESIGN.md`. For submit API exposure of
`candidate_kind` or compact `api_evidence`, also read
`docs/60_api_candidate/06_S7B_SUBMIT_API_REPORT_ONLY_EXTENSION_DESIGN.md`.

### Layer 3 - Deep Evidence Read

Open these only after Layer 2 shows the need:

```text
code and tests for the touched module
large knowledge packs
historical numbered docs
external repo README/docs audits
benchmark reports or ledger records
```

Layer 3 is for proof, implementation detail, or archaeology. It is not the default design context.

## Design Autonomy And External Assets

Agents may design the next step from active docs without asking the owner to restate the project
direction every turn, but the autonomy is bounded:

- Layer 1 is mandatory for every design.
- Layer 2 is selected by the active task.
- Layer 3 is opened only for proof, implementation detail, or a focused external README audit.
- Active docs and verified code/tests win over old archive docs.
- External repositories, papers, tools, and datasets must first map to an intake shape in
  `docs/knowledge/EXTERNAL_ASSET_MAPPING_MATRIX.md`.

External assets may be used in these ways only:

```text
knowledge_note    -> borrow a design lesson or warning
readme_audit      -> shallow-read README/docs and record facts
manifest_seed     -> store pinned metadata only
dataset_slice     -> owner-approved tiny pinned subset only
producer_adapter  -> treat output as candidate input
executor_adapter  -> design runner/evidence/parser first
sut_target        -> pin as a target, do not vendor source
isolation_support -> use only after Asset Gate/API design requires it
```

No design should clone, copy, install, vendor, or execute an external asset merely because it
appears in a knowledge file. That requires a named project artifact, expected evidence, red lines,
and owner-approved implementation scope.

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

Large knowledge files are reference packs, not active plans:

```text
docs/knowledge/EXTERNAL_ECOSYSTEM_KNOWLEDGE_PACK.md
docs/knowledge/EXTERNAL_AGENT_AND_TESTGEN_KB.md
docs/knowledge/AGENT_HARNESS_EVALUATION_KB.md
docs/knowledge/BENCHMARK_SOURCES_AND_STRATEGY.md
docs/knowledge/INTERNET_TECH_BUSINESS_KB.md
```

Use them through Layer 2/3 routing only. Do not compact them into the default context and do not
resolve conflicts by averaging them with current active docs.

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
