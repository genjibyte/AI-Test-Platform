# AGENTS.md - agent operating guide for TestAgent Lab

> Read this first, every session. Short on purpose. If reality conflicts with this
> file, trust the repo and fix this file.

## Thesis (what this project is)

An execution-based candidate evaluation platform for test-generating agents. It judges whether a
candidate test has engineering value; it does not "generate tests." Candidates may come from the
built-in generator, Codex, Copilot, DeepSeek, Coze/Dify, EvoSuite/Randoop/Schemathesis, or a human.
Generation is just one producer.
The built-in JUnit generator is a legacy failed exploration kept only because deletion is costly
and it still provides a removable compatibility producer. It must not steer roadmap priority.

The product is the judge -> quality gate -> review recommendation -> badcase ledger ->
reproducible report layer. The current kernel is Java/Maven test execution through
Maven/Surefire/JaCoCo; JUnit is a thin compatibility path, and TestNG should be visible as an
enterprise Java framework without becoming a separate product. The mainline should make early room
for interface/API-test candidate evaluation using the same judge kernel. API/interface is a
near-term candidate-evaluation direction, not a separate product.

Mainline framing:

- Entry: interface/API test candidates and automated test-generation outputs. Generation is an
  input source, not the platform identity.
- Goals: improve integration-test quality, final code quality, and architecture-quality feedback
  through executable evidence.
- Platform form: execute, judge, attribute, and precipitate badcases. Do not become the test
  generator, API automation framework, task platform, or auto-adoption system.

See `docs/00_foundation/40_CORE_THESIS_REPOSITIONING.md` section 10,
`docs/knowledge/OPEN_SOURCE_REUSE_GOVERNANCE_2026_07.md`,
`docs/knowledge/EXTERNAL_ASSET_MAPPING_MATRIX.md`,
`docs/knowledge/EXTERNAL_ASSET_PHASE_PLAN.md`,
`docs/knowledge/EXTERNAL_PROJECT_AND_BENCHMARK_REGISTRY.md`, and
`docs/00_foundation/00_PROJECT_CHARTER.md`.

Out of scope unless owner-approved: UI automation, manual test-case authoring, generic RAG,
knowledge graph, multi-agent platform, enterprise task management, and becoming an API-automation
framework. The sanctioned API direction is API/interface candidate evaluation: design candidate
kinds, evidence contracts, report fields, and small smoke paths; start executors only after an
owner-gated design is approved.

## Design north-star

1. Build order: do not overfit to unit-only work.
   - Minimal trustworthy unit-test judge kernel: done.
   - Producer-agnostic abstraction spanning AI unit tests to interface/API test code and cases:
     mainline direction.
   - Minimal owner-gated API evaluation smoke paths only after the design matures.
   Early API/interface design should start from Entry/Goals/Form: candidate inputs first,
   integration/code/architecture quality goals second, and execution/judgment/attribution/badcase
   precipitation as the platform form.
2. Four pillars. Every feature must state which pillar it strengthens for candidates of any origin:
   - Candidate: author-agnostic submission entry (`submit_candidate`, docs/53). Live.
   - Provenance: who produced it; advisory, never a warrant (`producer_id` plus
     `run_kind="external"`, docs/53 S2). Live.
   - Badcase: structured, retrievable failure precipitation (`app/ledger/` plus retrieval,
     docs/50). Live.
   - Asset Gate: judge whether the assets (code context, business-oracle source, fixtures, mock,
     schema) suffice, and recommend test level (unit, api, integration, manual-oracle-first).
     Judge-side, advisory. S1-S4A live: compact report, benchmark/ledger carry, descriptive
     breakdowns, and a report-only Test-Level Router. No executor/API harness.
3. Single anti-drift filter: does this strengthen judging, managing, comparing, or precipitating
   candidates of any origin? If it only raises the built-in generator's compile/pass rate and is
   not an oracle-safety or red-line fix, downgrade it.
4. Invariants hold across all of the above: advisory only; never auto-accept; `conclusion` stays
   `NEED_HUMAN_REVIEW`; `trusted=False`; every new level/phase is owner-gated and design-first.
   Design-first means API/interface candidate evaluation should be considered early, not hidden
   behind endless unit-test generator tuning.

## Boundary

The project's claim is not "I can generate tests." It is "I can judge whether an AI-generated test
actually has engineering value." That inversion is the whole point, and it exists to resist LLM
hallucination and fake/green-but-empty tests.

- A generated, green, or high-coverage test is a candidate, never a result. It is only worth
  anything after it survives judging: compile -> execute -> quality gate -> review. The conclusion
  stays `NEED_HUMAN_REVIEW`.
- Never present a generated or fake-client test as a working or valuable test. Never claim a test
  passes or has value without command evidence from the judge layer.
- Coverage up is not correctness. Green is not useful by itself. The product is the judgment, not
  the output.
- If you cannot show judging evidence, say so. Do not fill the gap with a confident-sounding but
  unverified claim.

## Current state

- Done: judge plus minimal generation pipeline; `submit_candidate`; quality gate plus review
  policy; preflight plus oracle-safe compile-repair gated off; ledger P1/P2 plus retrieval;
  `run_kind` hygiene; business-invariant tags; oracle-strength structural estimate; dormant gated
  PIT mutation subsystem; invariant review; survived-mutant classification; mock smell; review
  digest.
- Asset Gate S1-S4A is live: `review_summary["asset_sufficiency"]`, tiny `asset_facts` from
  `ContextSnapshot`, digest flags, compact benchmark/ledger carry fields, descriptive breakdowns,
  benchmark markdown, and report-only `review_summary["test_level_router"]`. All are advisory.
  The router launches no executor and creates no API/integration candidate kind.
- API/interface S6C-S10D is report/submit/projection/display/compact-ledger-carry/pure-ledger
  projection only. No API executor, service orchestration, SQLite column/index, digest severity
  change, retrieval scoring, existing analytics change, badcase signature change, or verdict
  change is live.
- S6F human/golden label metric readiness is pure summary only. It can say which supplied labels
  make usable/edit/time/RCA/misjudgment/defect metrics computable, but it cannot persist labels,
  create headline claims, alter digest severity, or change verdict/trust.
- S6G Golden Set defect-denominator readiness is metadata-only. It can identify future
  defect-discovery denominator candidates from `manifest_seed` records, but it cannot materialize
  datasets, execute verifiers, create headline metrics, or change verdict/trust.
- S6H change-set handoff classification adds a `landing_readiness_snapshots` review batch for
  project progress and human/golden metric readiness paths. It is handoff-only and grants no git,
  executor, persistence, headline metric, verdict, or trust authority.
- S6I landing-readiness rollup combines project progress, supplied human/golden labels, and
  supplied Golden Set seed metadata into one planning view. It creates no new metric, persistence,
  dataset slice, verifier execution, release gate, headline claim, verdict, or trust authority.
- S6J landing-readiness Markdown presentation renders an existing snapshot for human handoff only.
  It does not recompute readiness, wire default reports, create release/headline claims, or change
  verdict/trust.
- S6K landing-readiness review aids add blocker-derived `review_questions` and
  `evidence_checklist` fields to the snapshot and Markdown. They do not collect evidence, approve
  dataset/verifier work, create release/headline claims, or change verdict/trust.
- S6L landing-readiness snapshot validation checks schema, review-aid structure, and top-level/
  nested no-authority flags before Markdown rendering. Forged headline, dataset, verifier,
  verdict, or trust authority is rejected instead of displayed as normal handoff material.
- S6M landing-readiness typed validation checks percent ranges, stage/band enum values,
  source-version consistency, non-negative input counts, human-ready metric count consistency, and
  nested progress/top-level alignment. It still does not recompute readiness or create any
  release/headline/verdict/trust authority.
- S6N landing-readiness derived-consistency validation checks that blockers, next steps, input
  counts, human-ready metric names/counts, defect-denominator flags, review questions, and
  evidence-checklist statuses match nested readiness facts. It still does not scan the workspace,
  collect labels, materialize datasets, execute verifiers, or create release/headline/verdict/trust
  authority.
- S6O landing-readiness blocker-family summary projects a validated snapshot into project-progress,
  human-label, Golden Set denominator, and change-batch review families for human audit. It is a
  review-navigation aid only and grants no workspace scan, evidence collection, release/headline,
  recommendation, conclusion, verdict, or trust authority.
- S6P landing-readiness blocker-summary validation checks standalone blocker-family handoff
  artifacts for schema, count, clearance-status, next-clearance, and no-authority drift. It grants
  no source recompute, evidence collection, release/headline, recommendation, conclusion, verdict,
  or trust authority.
- S6Q landing-readiness blocker-summary Markdown presentation renders standalone blocker-family
  summaries after validation for human handoff. It grants no source recompute, default report
  wiring, evidence collection, release/headline, recommendation, conclusion, verdict, or trust
  authority.
- S6 landing-readiness governance is frozen after S6Q for normal progress work. Do not add S6R/S6S
  validators, projections, or Markdown handoff layers unless a concrete high-risk boundary bug is
  found. Next progress must target one joint human-label + Golden Set evidence closure slice.
  API/interface implementation design is lower priority until that joint slice exposes a concrete
  need.
- S6D/S6D2 Java framework neutrality is report-only: JUnit4/JUnit5/TestNG/mixed/unknown facts may
  surface in `review_summary["java_test_framework"]`, and `submit_candidate` may optionally carry
  a normalized framework declaration, but framework choice cannot install dependencies, mutate
  POMs, choose a runner, change digest severity, or affect verdict/trust.
- Governance S5D is metadata/design only: external asset phase policy, mandatory design reuse
  checks, knowledge embedding destination routing, README audit validation, change-set handoff,
  and Skill/SOP blueprint readiness. These do not install Skills, call models, execute external
  tools, or change verdict/trust.
- S6E project progress snapshot is advisory metadata only. Current weighted estimate is about
  71%, not 80%; the helper grants no runtime, git, executor, digest, verdict, or trust authority.
- Still not built without explicit approval: API/interface executor, implemented new candidate
  kinds, Defects4J ingestion, multi-model experiments, LLM Judge scoring, complex RAG, large MCP
  or web backend, auto-adoption, auto-merge, auto-warehouse entry, installed Codex Skill runtime,
  external SUT execution, Docker/service orchestration, or external DB connection.
- Legacy JUnit generation and prompt/pass-rate work are downgraded producer support. Continue only
  for deletion-safe maintenance, offline demo compatibility, or false-trust/oracle-safety fixes.
- Branch `main`; commits are often stacked locally and unpushed.
- Data caveat: new benchmark runs carry authoritative `run_kind`. Historical
  `var/benchmark/*/bench.db` rows have no field, so fake/real split stays heuristic. Historical
  data is read-only; never backfill.

## Read first

Always read the thin layer:

1. `docs/WORK_LOG.md` - current snapshot, next step, and routed read rules.
2. `docs/README.md` - active doc index, archive policy, and three-layer read mechanism.
3. `docs/00_foundation/54_CORE_FREEZE_AND_BOUNDARY_REFERENCE.md` - current boundary.
4. `docs/knowledge/README.md` - knowledge gate for design work.
5. `docs/knowledge/EXTERNAL_ASSET_MAPPING_MATRIX.md` - required intake-shape mapping.

Then follow the three-layer read mechanism in `docs/README.md`:

- Layer 1: current state, boundary, knowledge gate, and asset mapping.
- Layer 2: only docs needed by the current design need.
- Layer 3: historical docs, large knowledge packs, external repo README audits, and code/tests only
  when Layer 2 proves they are needed.
- Mandatory reuse check: every design input must state source/source family, intake shape, project
  artifact, expected evidence, and red lines before inventing a new mechanism. Use
  `app.governance.validate_design_reuse_check(...)` and
  `app.governance.design_reuse_check_plan(...)` for metadata validation/summary. These grant no
  clone/install/vendor/execute/verdict/trust authority.
- For API/interface design, start from
  `app.governance.api_interface_candidate_reuse_check_plan(...)` and adapt it before proposing a
  new mechanism.
- After choosing an intake shape, use `app.governance.knowledge_embedding_destination(...)` or
  `docs/knowledge/README.md` to decide which docs should receive the summary.
- If an article recommends Skill usage, adapt it as an evaluation Skill/SOP blueprint over the
  existing judge workflow first. Use `app.governance.validate_judge_skill_blueprint(...)`,
  `app.governance.judge_skill_readiness_plan(...)`, or
  `app.governance.candidate_eval_skill_readiness_plan(...)`; these grant no Skill install,
  runtime, model-call, executor, verdict, or trust authority.

Task-routed examples:

- API/interface candidate design: `docs/00_foundation/40_CORE_THESIS_REPOSITIONING.md` section 10
  and `docs/60_api_candidate/00_API_CANDIDATE_JUDGE_BOUNDARY.md`.
- API compact report/evidence or S6C/S7 smoke-path work:
  `docs/60_api_candidate/03_API_COMPACT_REPORT_CONTRACT.md` and
  `docs/60_api_candidate/04_S7_SMOKE_PATH_SELECTION.md`; add S7/S8/S9/S10 docs only when the task
  reaches those report-only paths.
- Asset Gate / Test-Level Router: `docs/50_benchmark/55_ASSET_GATE_NEXT_STEP_AUDIT.md`.
- Metrics, benchmark claims, landing validation, or historical data:
  `docs/00_foundation/42_AI_TEST_FAILURE_EMPIRICAL_AUDIT.md`,
  `docs/50_benchmark/43_RUN_KIND_DESIGN.md`, and
  `docs/50_benchmark/56_REAL_WORLD_VALIDATION_LINE.md`.
- Human-review labels, RCA, usable-test rate, diagnosis time, or misjudgment metrics:
  `docs/50_benchmark/56_REAL_WORLD_VALIDATION_LINE.md` and
  `docs/50_benchmark/57_HUMAN_REVIEW_RCA_LABEL_CONTRACT.md`.
- External repositories/assets: first map each asset with
  `docs/knowledge/EXTERNAL_ASSET_MAPPING_MATRIX.md`; for project/benchmark names also check
  `docs/knowledge/EXTERNAL_ASSET_PHASE_PLAN.md` and
  `docs/knowledge/EXTERNAL_PROJECT_AND_BENCHMARK_REGISTRY.md`; record focused audits in
  `docs/knowledge/EXTERNAL_REPO_README_AUDIT.md` when the matrix says `readme_audit`,
  `dataset_slice`, `executor_adapter`, or `sut_target`.
- Documentation cleanup or architecture audit:
  `docs/00_foundation/61_CURRENT_DOCS_AND_ARCHITECTURE_AUDIT.md`.

External asset rule: never write only "useful". State the intake shape (`knowledge_note`,
`readme_audit`, `manifest_seed`, `dataset_slice`, `producer_adapter`, `executor_adapter`,
`sut_target`, `isolation_support`, `provenance_support`, `discovery_index`, `support_only`, or
`reject_mainline`) and the project artifact it affects.

## Toolchain

- Python: use the venv: `& "E:\AI-Test-Platform\.venv\Scripts\python.exe"`.
  Bare `python` is the Windows Store stub.
- Verify command:
  `& "E:\AI-Test-Platform\.venv\Scripts\python.exe" -m pytest`
  Recent evidence: `747 passed, 4 skipped, 1 warning in 6.92s`.

## Safe actions

- Read/inspect anything; run offline `pytest`; run read-only scripts
  (`scripts/audit_bench.py`, `scripts/run_judge.py`).
- Edit code only for an explicitly approved, bounded task; keep diffs small; run tests after each
  change.
- Write designs to `docs/`; commit locally with a clear message.

## Forbidden

- No auto-accept (`conclusion` stays `NEED_HUMAN_REVIEW`, `trusted=False`); no oracle auto-fix.
- No production-code, `pom.xml`, or existing-test edits as part of generation; no auto-commit.
- Never read, print, summarize, or commit `.env`. API keys only via env, never logged.
- No real model/API calls without explicit user confirmation, command, and cost.
- No broad refactors, architecture changes, or new dependencies unless owner-approved.

## Fake / dry-run / smoke / real-model hygiene

- Fake output is the `FakeLLMClient` placeholder (`// FAKE CLIENT PLACEHOLDER`,
  `model="fake-1"`). It is not real-model data.
- Any headline metric or ledger claim must be computed over real-model rows only. Until a
  `run_kind` field exists, separation is heuristic; say so and never present it as exact.
- Reproduce numbers with `scripts/audit_bench.py`, not by hand.

## Test safety

- Tests must never contact a real LLM. `tests/conftest.py` forces the offline fake provider and
  blocks the HTTP call unless `TESTAGENT_E2E=1`.
- Keep that guard; do not disable it; do not make a unit test depend on a real provider.

## Multi-agent workflow

- Codex: implementation, only after an approved bounded task.
- Codex research/design: docs/design only, no code unless asked.
- Codex reviewer: audit/review only; a reviewer does not rewrite code.
- Human: final decision, push, API-key/cost approval.
- One agent per worktree at a time. Hand off with what changed, files, commands and results,
  what is unpushed.

## Push policy

- Push is human-only. Agents commit locally; never `git push`.
- Surface the unpushed commit count in every handoff.

## Evidence rule

- Never claim success without command evidence. "Tests pass" must show the actual pytest summary
  line. "Numbers reproduce" must show the `scripts/audit_bench.py` output.
