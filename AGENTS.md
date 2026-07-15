# AGENTS.md — agent operating guide for TestAgent Lab

> Read this first, every session. Short on purpose. If reality conflicts with this
> file, trust the repo and fix this file.

## Thesis (what this project is)
An **execution-based _candidate evaluation_ platform for test-generating agents.** It
judges whether a candidate test has engineering value; it does **not** "generate tests."
Candidates may come from the built-in generator, Codex, Copilot, Codex, DeepSeek,
Coze/Dify, EvoSuite/Randoop/Schemathesis, or a human — **generation is just one producer.**
The product is the **judge → quality gate → review recommendation → badcase ledger →
reproducible report** layer. The current kernel is **Java/Maven JUnit unit tests**, but the
mainline should make early room for **interface/API-test candidate evaluation** using the same
judge kernel. API/interface is a near-term candidate-evaluation direction, not a separate product.

Mainline framing:
- **Entry:** interface/API test candidates and automated test-generation outputs. Generation is an
  input source, not the platform identity.
- **Goals:** improve integration-test quality, final code quality, and architecture-quality
  feedback through executable evidence.
- **Platform form:** execute, judge, attribute, and precipitate badcases. Do not become the test
  generator, API automation framework, task platform, or auto-adoption system.

See `docs/00_foundation/40_CORE_THESIS_REPOSITIONING.md` (§10 = the V2 widening),
`docs/knowledge/EXTERNAL_ECOSYSTEM_KNOWLEDGE_PACK.md`, and the charter
`docs/00_foundation/00_PROJECT_CHARTER.md`.
Out of scope (unless owner-approved): UI automation, manual test-case authoring, generic
RAG / knowledge-graph / multi-agent platform, enterprise task management, and **becoming an
API-automation framework**. The sanctioned API direction is **API/interface candidate
evaluation**: design candidate kinds, evidence contracts, report fields, and small smoke paths;
start executors only after an owner-gated design is approved.

## Design north-star (every new design must pass this)
1. **Build order — don't overfit to unit-only work:** (1) a minimal trustworthy **unit-test judge
   kernel** *(done)*; (2) the producer-agnostic abstraction below, spanning AI unit tests →
   interface/API test code & cases *(mainline direction)*; (3) then minimal owner-gated API
   evaluation smoke paths as the design matures. Do not let producer/generator polish crowd out
   S6 API/interface candidate design.
   Early API/interface design should start from the Entry/Goals/Form framing above:
   candidate inputs first, integration/code/architecture quality goals second, execution/judgment/
   attribution/badcase precipitation as the platform form.
2. **Four pillars.** Every feature must state which pillar it strengthens, for *candidates of
   any origin* (not "make our own generator greener"):
   - **Candidate** — author-agnostic submission entry (`submit_candidate`, docs/53). *Live.*
   - **Provenance** — who produced it; advisory, never a warrant (`producer_id` + `run_kind=
     "external"`, docs/53 S2). *Live.*
   - **Badcase** — structured, retrievable failure precipitation (`app/ledger/` + retrieval,
     docs/50). *Live.*
   - **Asset Gate** — judge whether the *assets* (code context / business-oracle source /
     fixtures / mock / schema) suffice, and recommend the test **level** (unit / api /
     integration / manual-oracle-first). Judge-side, advisory. **S1-S4A live:** compact report,
     benchmark/ledger carry, descriptive breakdowns, and a report-only Test-Level Router. No
     executor/API harness.
3. **Single anti-drift filter:** does this strengthen *judging / managing / comparing /
   precipitating* candidates of any origin? If it only raises our own generator's compile/pass
   rate — and is not an oracle-safety / red-line fix — **downgrade it.**
4. **Invariants hold across all of the above:** advisory only; never auto-accept; `conclusion`
   stays `NEED_HUMAN_REVIEW`; `trusted=False`; every new level/phase is owner-gated + design-first.
   "Design-first" means API/interface candidate evaluation should be considered early, not hidden
   behind endless unit-test generator tuning.

## Boundary — the bar every agent is held to (anti-hallucination)
The project's claim is **NOT "I can generate tests"** — it is **"I can judge whether
an AI-generated test actually has engineering value."** That inversion is the whole
point, and it exists specifically to resist LLM hallucination and fake/green-but-empty
tests:
- A generated / green / high-coverage test is a **candidate**, never a result. It is
  only worth anything **after** it survives judging: compile → execute → quality gate →
  review, and the conclusion stays `NEED_HUMAN_REVIEW`.
- **Never present a generated or fake-client test as a working or valuable test.** Never
  claim a test "passes" or "has value" without command evidence from the judge layer.
- Coverage up ≠ correct. Green ≠ useful. The product is the *judgment*, not the output.
- If you cannot show judging evidence, say so — do not fill the gap with a confident-
  sounding but unverified claim.

## Current state (2026-07-04)
- Done: judge + minimal generation pipeline; `submit_candidate`; quality gate + review policy
  (advisory, never auto-accept); preflight + oracle-safe compile-repair (gated off); ledger
  P1/P2 + retrieval; `run_kind` hygiene (`real` headline excludes fake/dryrun/smoke/external/
  historical unknown); business-invariant tags; oracle-strength structural estimate; dormant
  gated PIT mutation subsystem; invariant review; survived-mutant classification; mock smell;
  review digest.
- Asset Gate S1-S4A is live: `review_summary["asset_sufficiency"]`, tiny `asset_facts` from
  `ContextSnapshot`, digest flags, compact benchmark/ledger carry fields, descriptive breakdowns,
  benchmark markdown, and report-only `review_summary["test_level_router"]`. All are advisory.
  The router launches no executor and creates no API/integration candidate kind.
- Still **not** built — do not start without explicit approval: API/interface executor,
  implemented new candidate kinds, Defects4J ingestion, multi-model experiments, LLM Judge scoring,
  complex RAG, large MCP/web backend, auto-adoption, auto-merge, or auto-warehouse entry.
- Current direction: avoid treating API/interface evaluation as indefinitely deferred. After a
  bounded S4A router audit, prefer S6 API/interface candidate boundary design over more unit-test
  generator, prompt, or compile/pass-rate work unless a concrete evidence/red-line fix is being
  handled.
- Branch `main`; commits are often stacked **locally and unpushed**.
- Data caveat: **new** benchmark runs carry the authoritative `run_kind` field;
  **historical** `var/benchmark/*/bench.db` rows have no field, so their fake/real split
  stays heuristic (`scripts/audit_bench.py`, labeled). Historical data is read-only —
  never backfilled (see `docs/00_foundation/42_AI_TEST_FAILURE_EMPIRICAL_AUDIT.md` §A,
  `docs/50_benchmark/43_RUN_KIND_DESIGN.md`).

## Read first
Use a small read set so design work stays on the mainline and does not hallucinate from old
notes.

Always read the thin layer:
1. `docs/WORK_LOG.md` — current snapshot, next step, and routed read rules
2. `docs/README.md` — active doc index, archive policy, and three-layer read mechanism
3. `docs/00_foundation/54_CORE_FREEZE_AND_BOUNDARY_REFERENCE.md` — current boundary
4. `docs/knowledge/README.md` — knowledge gate for design work
5. `docs/knowledge/EXTERNAL_ASSET_MAPPING_MATRIX.md` — required intake-shape mapping for external assets

Then follow the three-layer read mechanism in `docs/README.md`:
- Layer 1, thin required read: current state, boundary, knowledge gate, and asset mapping.
- Layer 2, task-routed read: only docs needed by the current design need.
- Layer 3, deep/evidence read: historical docs, large knowledge packs, external repo README audits,
  and code/tests only when Layer 2 proves they are needed.

Task-routed examples:
- API/interface candidate design: `docs/00_foundation/40_CORE_THESIS_REPOSITIONING.md` §10 and
  `docs/60_api_candidate/00_API_CANDIDATE_JUDGE_BOUNDARY.md`.
- API compact report/evidence or S6C/S7 smoke-path work:
  `docs/60_api_candidate/03_API_COMPACT_REPORT_CONTRACT.md` and
  `docs/60_api_candidate/04_S7_SMOKE_PATH_SELECTION.md`. For `junit_api_candidate` report-only
  wiring, also read `docs/60_api_candidate/05_S7A_JUNIT_API_REPORT_ONLY_WIRING_DESIGN.md`. For
  submit API exposure of `candidate_kind` or compact `api_evidence`, also read
  `docs/60_api_candidate/06_S7B_SUBMIT_API_REPORT_ONLY_EXTENSION_DESIGN.md`.
- Asset Gate / Test-Level Router: `docs/50_benchmark/55_ASSET_GATE_NEXT_STEP_AUDIT.md`.
- Metrics, benchmark claims, landing validation, or historical data:
  `docs/00_foundation/42_AI_TEST_FAILURE_EMPIRICAL_AUDIT.md`,
  `docs/50_benchmark/43_RUN_KIND_DESIGN.md`, and
  `docs/50_benchmark/56_REAL_WORLD_VALIDATION_LINE.md`.
- Human-review labels, RCA, usable-test rate, diagnosis time, or misjudgment metrics:
  `docs/50_benchmark/56_REAL_WORLD_VALIDATION_LINE.md` and
  `docs/50_benchmark/57_HUMAN_REVIEW_RCA_LABEL_CONTRACT.md`.
- External repositories/assets: first map each asset with
  `docs/knowledge/EXTERNAL_ASSET_MAPPING_MATRIX.md`, then do a focused README audit when the
  matrix says `readme_audit`, `dataset_slice`, `executor_adapter`, or `sut_target`. Do not make all
  knowledge packs part of the default read set.

External asset rule: never write only "useful". State the intake shape (`knowledge_note`,
`readme_audit`, `manifest_seed`, `dataset_slice`, `producer_adapter`, `executor_adapter`,
`sut_target`, `isolation_support`, `provenance_support`, `discovery_index`, `support_only`, or
`reject_mainline`) and the project artifact it affects.

## Toolchain (this machine)
- Python: **use the venv** → `& "E:\AI-Test-Platform\.venv\Scripts\python.exe"`.
  Bare `python` is the Windows Store stub (exits 49, no output).
- Verify command:
  `& "E:\AI-Test-Platform\.venv\Scripts\python.exe" -m pytest` → recent evidence:
  `427 passed, 4 skipped, 1 warning` (the count grows as tests are added).

## Safe actions
- Read/inspect anything; run offline `pytest`; run read-only scripts
  (`scripts/audit_bench.py`, `scripts/run_judge.py`).
- Edit code only for an explicitly approved, bounded task; keep diffs small; run tests
  after each change.
- Write designs to `docs/`; commit locally with a clear message.

## Forbidden
- No auto-accept (`conclusion` stays `NEED_HUMAN_REVIEW`, `trusted=False`); no oracle
  auto-fix (never rewrite expected→actual, never weaken/delete assertions).
- No production-code / pom / existing-test edits as part of generation; no auto-commit.
- **Never read, print, summarize, or commit `.env`.** API keys only via env, never logged.
- No real model/API calls without explicit user confirmation (state command + cost first).
- No broad refactors, no architecture changes, no new dependencies (if truly needed:
  stop and ask).

## Fake / dry-run / smoke / real-model hygiene
- Fake output is the `FakeLLMClient` placeholder (`// FAKE CLIENT PLACEHOLDER`,
  `model="fake-1"`). **It is NOT real-model data.**
- Any headline metric or ledger claim must be computed over **real-model rows only**.
  Until a `run_kind` field exists, separation is **heuristic** (placeholder string /
  `model=="fake-1"`) — say so; never present it as exact.
- Reproduce numbers with `scripts/audit_bench.py` (read-only), not by hand.

## Test safety
- Tests must never contact a real LLM. `tests/conftest.py` forces the offline fake
  provider and blocks the HTTP call **unless `TESTAGENT_E2E=1`** (the e2e opt-in).
  Keep that guard; do not disable it; do not make a unit test depend on a real provider.

## Multi-agent workflow
- Codex: implementation, only after an approved bounded task.
- Codex (research/design): docs/design only, no code unless asked.
- Codex / reviewer: audit/review only — **a reviewer does not rewrite code.**
- Human: final decision, push, API-key/cost approval.
- One agent per worktree at a time. Hand off with: what changed, files, commands+results,
  what's unpushed.

## Push policy
- **Push is human-only.** Agents commit locally; never `git push`. Surface the unpushed
  commit count in every handoff.

## Evidence rule
- Never claim success without command evidence. "Tests pass" must show the actual
  pytest summary line; "numbers reproduce" must show the `scripts/audit_bench.py` output.
