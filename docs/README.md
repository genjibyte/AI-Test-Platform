# TestAgent Lab Docs

> Goal: reduce doc-driven hallucination. Read the active set first; pruned historical docs should
> be recovered from git history only when a task explicitly needs archaeology.

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

### Mandatory Reuse Check

Every design input must include an explicit reuse check before proposing new project-specific
mechanisms. Prefer borrowing and adapting proven ideas from the curated knowledge base, external
project registry, papers/articles, tools, evaluation sets, and existing code patterns so the
platform avoids rebuilding wheels. The reuse check must state the source or source family, the
intake shape, the project artifact it affects, and the boundary that prevents drift.

This rule does not authorize cloning, copying, installing, vendoring, or executing external code by
default. Reuse starts as `knowledge_note`, `readme_audit`, `manifest_seed`, or another mapped
intake shape, then advances only through the phase plan and owner-gated implementation scope. The
pure helper `app.governance.validate_design_reuse_check(...)` validates this metadata contract and
grants no runtime authority. Use `app.governance.design_reuse_check_plan(...)` to summarize a
design's reuse checks before review; an empty plan is not ready for design review. For the next
API/interface candidate design pass, `app.governance.api_interface_candidate_reuse_check_plan(...)`
provides a ready metadata-only reuse plan over active registry/matrix sources.
Use `app.governance.knowledge_embedding_destination(...)` after choosing an intake shape to decide
which docs should receive the summary.

### Layer 2 - Task-Routed Read

Read only the docs needed by the active design need:

| Task | Read additionally |
|---|---|
| API/interface candidate mainline | Preferred next direction after S4A closeout: [40 Core Thesis Repositioning §10](/docs/00_foundation/40_CORE_THESIS_REPOSITIONING.md), [API Candidate Judge Boundary](/docs/60_api_candidate/00_API_CANDIDATE_JUDGE_BOUNDARY.md), [Minimal Judge Contract](/docs/60_api_candidate/01_MINIMAL_JUDGE_CONTRACT.md), [API Candidate Boundary Design](/docs/60_api_candidate/02_API_CANDIDATE_BOUNDARY_DESIGN.md) |
| Java test framework neutrality / TestNG visibility | [Java Test Framework Neutrality](/docs/60_api_candidate/10_JAVA_TEST_FRAMEWORK_NEUTRALITY.md) |
| Project progress / completion estimate | [Project Progress Snapshot](/docs/00_foundation/63_PROJECT_PROGRESS_SNAPSHOT.md) |
| Asset Gate / Test-Level Router | [55 Asset Gate Design Digest](/docs/50_benchmark/55_ASSET_GATE_NEXT_STEP_AUDIT.md) |
| Benchmark metrics or historical data | [42 AI Test Failure Empirical Audit](/docs/00_foundation/42_AI_TEST_FAILURE_EMPIRICAL_AUDIT.md), `docs/50_benchmark/43_RUN_KIND_DESIGN.md`; for Golden Set manifest governance also read `docs/50_benchmark/23_BENCHMARK_MANIFEST.md` and `docs/50_benchmark/62_GOLDEN_SET_MANIFEST_GOVERNANCE.md`; for API smoke projection also read `docs/50_benchmark/59_API_SMOKE_BENCHMARK_PROJECTION_DESIGN.md`; for API smoke ledger projection also read `docs/50_benchmark/60_API_SMOKE_LEDGER_PROJECTION_DESIGN.md` |
| External assets or repo intake | [External Asset Mapping Matrix](/docs/knowledge/EXTERNAL_ASSET_MAPPING_MATRIX.md), [External Asset Phase Plan](/docs/knowledge/EXTERNAL_ASSET_PHASE_PLAN.md), [External Project And Benchmark Registry](/docs/knowledge/EXTERNAL_PROJECT_AND_BENCHMARK_REGISTRY.md), [External Repo README Audit](/docs/knowledge/EXTERNAL_REPO_README_AUDIT.md), then a focused README audit when the matrix calls for it |
| External lessons / skills / harness patterns | [Knowledge Index](/docs/knowledge/README.md), then only the named knowledge file |
| Governance / context recovery / reuse prep | [58 Governance, Recovery, And Reuse Preparation](/docs/00_foundation/58_GOVERNANCE_RECOVERY_AND_REUSE_PREP.md), [61 Current Docs And Architecture Audit](/docs/00_foundation/61_CURRENT_DOCS_AND_ARCHITECTURE_AUDIT.md), [Open Source Reuse Governance Digest](/docs/knowledge/OPEN_SOURCE_REUSE_GOVERNANCE_2026_07.md), and [Judge Skill SOP Templates](/docs/80_sop/00_JUDGE_SKILL_SOP_TEMPLATES.md) |

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
`docs/60_api_candidate/06_S7B_SUBMIT_API_REPORT_ONLY_EXTENSION_DESIGN.md`. For API smoke manifest,
exam-bag, first proof denominator, or asset requirements, also read
`docs/60_api_candidate/07_S7C_JUNIT_API_SMOKE_MANIFEST_DESIGN.md`. For manifest carry-through,
manifest/report alignment, `smoke_id` handling, or API-smoke denominator policy, also read
`docs/60_api_candidate/08_S7D_API_SMOKE_MANIFEST_CARRY_THROUGH_DESIGN.md` and
`docs/60_api_candidate/09_S8_API_SMOKE_DENOMINATOR_POLICY.md`. For API smoke benchmark projection,
also read `docs/50_benchmark/59_API_SMOKE_BENCHMARK_PROJECTION_DESIGN.md`. For API smoke ledger
projection, also read `docs/50_benchmark/60_API_SMOKE_LEDGER_PROJECTION_DESIGN.md`.

For broad documentation cleanup, context restoration, external reuse governance, Skill/SOP
preparation, or automation-boundary design, also read
`docs/00_foundation/58_GOVERNANCE_RECOVERY_AND_REUSE_PREP.md` and
`docs/00_foundation/61_CURRENT_DOCS_AND_ARCHITECTURE_AUDIT.md`. If the work mentions the
2026-07 open-source reuse note, read only the curated digest
`docs/knowledge/OPEN_SOURCE_REUSE_GOVERNANCE_2026_07.md` unless a focused external README audit is
explicitly needed.

### Layer 3 - Deep Evidence Read

Open these only after Layer 2 shows the need:

```text
code and tests for the touched module
large knowledge packs
git history for pruned historical docs
external repo README/docs audits
benchmark reports or ledger records
```

Layer 3 is for proof, implementation detail, or archaeology. It is not the default design context.
Pruned historical docs should be recovered from git history only when a task explicitly needs
archaeology.

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

Use `docs/knowledge/EXTERNAL_ASSET_PHASE_PLAN.md` to decide the earliest stage:
knowledge/README audit can happen now, manifest seeds belong to Golden Set governance, tiny
dataset/SUT slices are future owner-gated, producer/executor adapters come later, and platform
external databases wait until local ledger/report scale proves the need.

No design should clone, copy, install, vendor, or execute an external asset merely because it
appears in a knowledge file. That requires a named project artifact, expected evidence, red lines,
and owner-approved implementation scope.

When an external asset moves beyond a knowledge mention, include an asset record block as defined
in `docs/00_foundation/58_GOVERNANCE_RECOVERY_AND_REUSE_PREP.md` and
`docs/knowledge/EXTERNAL_ASSET_MAPPING_MATRIX.md`. This is still documentation metadata, not
approval to execute the asset.
When a new source needs to be summarized, use
`app.governance.knowledge_embedding_destination(...)` or the routing table in
`docs/knowledge/README.md` to pick the destination doc before editing.

When a generation-oriented article recommends Skill usage, adapt it as an evaluation Skill/SOP
only after it maps to an existing judge workflow. Use
`app.governance.validate_judge_skill_blueprint(...)`,
`app.governance.judge_skill_readiness_plan(...)`, or
`app.governance.candidate_eval_skill_readiness_plan(...)` to keep it metadata-only before any
owner-approved Codex Skill package or install.

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

Generation is only one producer. The built-in JUnit generator is a legacy failed exploration kept
only as removable compatibility support. Do not optimize the project around prompt quality,
generated pass rate, or JUnit-specific generation cleanup.

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
- `55` Asset Gate: S1-S3D live; S4A Test-Level Router is report-only live and S5A closeout
  audit is live; no executor, router carry, digest flag, signature, aggregate, or verdict change
- `09` API smoke denominator/red-lines: report-only denominator eligibility plus reviewer-facing
  red-line summary and optional Markdown rendering over evidence/manifest/authority boundaries;
  no endpoint, digest signal, executor, benchmark/ledger analytics, recommendation, conclusion, or
  trust change
- `59` API smoke benchmark projection: S9A helper, S9B conditional markdown, and S9C red-line
  descriptive counts live inside the named projection only; no generic aggregate key or ledger
- `60` API smoke ledger projection: S10A compact `JudgedRecord` JSON carry live, S10B named
  pure ledger projection helper live, S10C conditional Markdown presentation live, and S10D
  cross-layer benchmark/ledger projection boundary regression live; no SQLite column/index,
  existing analytics change, retrieval, signature, digest, executor, or verdict change
- `62` Golden Set manifest governance: S5B pure `manifest_seed` metadata validation/planning and
  S5B2 optional Markdown audit presentation live; no default benchmark report wiring, dataset
  content, download, executor, aggregate headline, ledger, digest, recommendation, conclusion,
  trusted-status, or manifest-pins change
- `S6D/S6D2` Java framework neutrality: JUnit/TestNG framework facts plus optional
  `submit_candidate` declaration carry are report-only; no dependency install, POM mutation,
  runner selection, digest signal, recommendation, conclusion, or trust change
- `S6F` human/golden label metric readiness: supplied human labels/projections can now be
  summarized for usable/edit/time/RCA/misjudgment/defect metric availability; no persistence,
  headline metric, digest, recommendation, conclusion, or trust authority
- `S6G` Golden Set defect-denominator readiness: `manifest_seed` metadata can now identify future
  defect-discovery denominator candidates; no dataset materialization, verifier execution,
  headline metric, recommendation, conclusion, or trust authority
- `63` project progress snapshot: pure governance helper estimates current overall completion at
  about 71%; no runtime, git, executor, digest, verdict, or trust authority
- `S6I` landing readiness rollup: combines project progress, supplied human/golden label
  readiness, and supplied Golden Set defect-denominator readiness into one planning view; no
  persistence, dataset/verifier authority, headline claim, recommendation, conclusion, or trust
  authority
- `S6J` landing readiness Markdown presentation: optional human handoff rendering over an existing
  snapshot; no recompute, default report wiring, release gate, headline claim, recommendation,
  conclusion, or trust authority
- `S6K` landing readiness review aids: snapshot and Markdown now include blocker-derived
  `review_questions` and `evidence_checklist`; no evidence collection, dataset/verifier approval,
  release/headline claim, recommendation, conclusion, or trust authority
- `S6L` landing readiness snapshot validator: pure schema/review-aid/no-authority validation used
  by the Markdown renderer; forged headline, dataset, verifier, verdict, or trust authority is
  rejected instead of rendered
- `S6M` landing readiness typed validator: percent, stage/band enum, source-version, input-count,
  metric-count, and nested progress consistency checks; still no recompute, evidence collection,
  release/headline claim, recommendation, conclusion, or trust authority
- `S6N` landing readiness derived-consistency validator: blockers, next steps, input counts,
  denominator flags, review questions, and evidence-checklist statuses must match nested
  readiness facts; still no recompute, evidence collection, release/headline claim,
  recommendation, conclusion, or trust authority
- `S6O` landing readiness blocker-family summary: validated snapshots can be projected into
  project-progress, human-label, Golden Set denominator, and change-batch review families for
  human audit; still no workspace scan, evidence collection, release/headline claim,
  recommendation, conclusion, or trust authority
- `S6P` landing readiness blocker-summary validator: standalone blocker-family summaries reject
  schema, count, clearance-status, next-clearance, and no-authority drift; still no source
  recompute, evidence collection, release/headline claim, recommendation, conclusion, or trust
  authority
- `S6Q` landing readiness blocker-summary Markdown presentation: standalone blocker-family
  summaries can be rendered after validation for human handoff; still no source recompute, default
  report wiring, evidence collection, release/headline claim, recommendation, conclusion, or trust
  authority
- S6 landing-readiness governance is frozen after S6Q for normal progress work; do not add S6R/S6S
  validators/projections/Markdown unless a concrete high-risk boundary bug appears. Next progress
  should create one joint human-label + Golden Set evidence closure slice. API/interface
  implementation design is lower priority until that joint slice exposes a concrete need.
- `S6H` landing readiness handoff classification: project progress and human/golden metric
  readiness paths now group into a dedicated review batch; no git action, persistence, headline
  metric, recommendation, conclusion, or trust authority
- `61` current docs/architecture audit: large raw KBs pruned, root README/CLAUDE simplified
- External asset phase policy: pure governance helper, README audit validator, and Golden Set
  metadata gate are live; no external download, install, execution, DB connection, dataset
  materialization, or vendored code
- CI/PR change-set handoff: pure status/evidence grouping helper, suggested commit batches,
  residual runtime/test warning, completed-track reclassification, runtime doc-reference cleanup
  classification, landing readiness snapshot batch, current API-smoke progress notes, Golden Set
  defect-denominator metadata-only notes, optional Markdown renderer, batch-path appendix,
  per-surface/per-batch status counts, per-batch surface counts, per-batch paths grouped by
  observed git status, per-batch review checklists, per-batch review gates, suggested verification
  targets, suggested commit-message hints, per-batch warning flags, top-level human-next-actions
  checklist, top-level batch-action summary, top-level batch-warning summary, top-level gate
  summary, and top-level verification-target summary are live; no git reads, staging, commit,
  push, merge, test execution, verdict authority, or trusted-status authority

None of these auto-accepts a candidate.

## Pruned Historical Docs

Old per-phase and superseded planning docs have been pruned from the working docs tree so they do
not pollute next-step design judgment. If archaeology is required, recover them from git history
instead of treating them as active context.

Large knowledge packs were pruned on 2026-07-21. They are not active plans and should be recovered
from git history only for explicit archaeology:

```text
docs/knowledge/EXTERNAL_ECOSYSTEM_KNOWLEDGE_PACK.md
docs/knowledge/EXTERNAL_AGENT_AND_TESTGEN_KB.md
docs/knowledge/AGENT_HARNESS_EVALUATION_KB.md
docs/knowledge/BENCHMARK_SOURCES_AND_STRATEGY.md
docs/knowledge/INTERNET_TECH_BUSINESS_KB.md
```

Use `docs/knowledge/OPEN_SOURCE_REUSE_GOVERNANCE_2026_07.md`,
`docs/knowledge/EXTERNAL_ASSET_MAPPING_MATRIX.md`, and
`docs/knowledge/EXTERNAL_PROJECT_AND_BENCHMARK_REGISTRY.md` instead of those raw packs for current
design.
Do not resolve conflicts by averaging deleted reference packs with current active docs.

Existing curated support docs:

- [Open Source Reuse Governance Digest](/docs/knowledge/OPEN_SOURCE_REUSE_GOVERNANCE_2026_07.md)
- [External Asset Phase Plan](/docs/knowledge/EXTERNAL_ASSET_PHASE_PLAN.md)
- [External Project And Benchmark Registry](/docs/knowledge/EXTERNAL_PROJECT_AND_BENCHMARK_REGISTRY.md)
- [Judge Skill SOP Templates](/docs/80_sop/00_JUDGE_SKILL_SOP_TEMPLATES.md)

Kept current docs include the thin layer, the charter/thesis/boundary references, active
benchmark/signal contracts, S6/S7 API candidate design, and curated knowledge/SOP files.

## Red Lines

- Never read, print, summarize, or commit `.env`.
- No real model/API calls without explicit user approval and cost disclosure.
- No auto-accept: `conclusion` stays `NEED_HUMAN_REVIEW`, `trusted=False`.
- No headline metrics over fake/dryrun/smoke/external/historical unknown rows.
- No new dependencies or broad architecture changes without explicit approval.
- No external asset execution, repair loop, PR sink, model gateway, or orchestration layer without
  an owner-approved design and no-verdict-drift tests.
