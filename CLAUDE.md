# CLAUDE.md — agent operating guide for TestAgent Lab

> Read this first, every session. Short on purpose. If reality conflicts with this
> file, trust the repo and fix this file.

## Thesis (what this project is)
An **execution-based _candidate evaluation_ platform for test-generating agents.** It
judges whether a candidate test has engineering value; it does **not** "generate tests."
Candidates may come from the built-in generator, Claude Code, Copilot, Codex, DeepSeek,
Coze/Dify, EvoSuite/Randoop/Schemathesis, or a human — **generation is just one producer.**
The product is the **judge → quality gate → review recommendation → badcase ledger →
reproducible report** layer. The current kernel is **Java/Maven JUnit unit tests**;
interface/API-test candidates are a **gated future level** (same judge kernel, new candidate
kind), not a new product.
See `docs/00_foundation/40_CORE_THESIS_REPOSITIONING.md` (§10 = the V2 widening),
`docs/knowledge/EXTERNAL_ECOSYSTEM_KNOWLEDGE_PACK.md`, and the charter
`docs/00_foundation/00_PROJECT_CHARTER.md`.
Out of scope (unless owner-approved): UI automation, manual test-case authoring, generic
RAG / knowledge-graph / multi-agent platform, enterprise task management, and **becoming an
API-automation framework** — judging API-test *candidates* with the same kernel is the only
sanctioned API direction, and only once a gated phase is approved.

## Design north-star (every new design must pass this)
1. **Build order — don't skip ahead:** (1) a minimal trustworthy **unit-test judge kernel**
   *(done)*; (2) the producer-agnostic abstraction below, spanning AI unit tests → interface/
   API test code & cases; (3) *only then* extend execution to interface/API testing.
2. **Four pillars.** Every feature must state which pillar it strengthens, for *candidates of
   any origin* (not "make our own generator greener"):
   - **Candidate** — author-agnostic submission entry (`submit_candidate`, docs/53). *Live.*
   - **Provenance** — who produced it; advisory, never a warrant (`producer_id` + `run_kind=
     "external"`, docs/53 S2). *Live.*
   - **Badcase** — structured, retrievable failure precipitation (`app/ledger/` + retrieval,
     docs/50). *Live.*
   - **Asset Gate** — judge whether the *assets* (code context / business-oracle source /
     fixtures / mock / schema) suffice, and recommend the test **level** (unit / api /
     integration / manual-oracle-first). Judge-side, advisory. **Not built — the next on-thesis step.**
3. **Single anti-drift filter:** does this strengthen *judging / managing / comparing /
   precipitating* candidates of any origin? If it only raises our own generator's compile/pass
   rate — and is not an oracle-safety / red-line fix — **downgrade it.**
4. **Invariants hold across all of the above:** advisory only; never auto-accept; `conclusion`
   stays `NEED_HUMAN_REVIEW`; `trusted=False`; every new level/phase is owner-gated + design-first.

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

## Current state (2026-06-17)
- Done: judge + minimal generation pipeline; quality gate + review policy (advisory,
  never auto-accept); preflight + oracle-safe compile-repair (gated off); ledger
  P1/P2 (`app/ledger/`); `run_kind` **minimal slice** (producer-set provenance + the
  "fake can never be real" guard, docs/43) plus its **S2 filter-only follow-up — done**
  (`aggregate()` + ledger analytics default headline views to `run_kind=="real"`;
  fake/dryrun/smoke + historical unknown excluded; back-compat; docs/43 §12).
  **Value-judgment signal layer (advisory; none feed the recommendation/`conclusion`),
  owner-approved 2026-06-13:** business-invariant tags (S1–S3, docs/45), oracle-strength
  **structural** estimate rolled up from the quality gate (S1+S2, docs/46), and a
  **dormant gated** PIT **mutation** subsystem (`app/mutation/`, `mutation_enabled=False`,
  docs/46 S3 — the real semantic signal; never runs PIT unless explicitly enabled).
- **Value-judgment signal layer landed (2026-06-13);** then judge-side problems
  #1/#3/#4/#5/#6 (docs/48–52) and the **producer-agnostic `submit_candidate` entry
  (docs/53 S1+S2)** landed (2026-06-15) — the **Candidate + Provenance + Badcase** pillars
  are live (see Design north-star). Mutation stays **gated off** (`mutation_enabled=False`);
  the JUnit5-aware PIT sidecar (`build_pit_pom`, `app/mutation/pit.py`) **is merged on `main`**
  (commit `c800a08`) and validated. Still **not** built — do not start without explicit
  approval: the **Asset Gate / Test-Level Router** (the next on-thesis step), the interface/
  API-test level, Defects4J, multi-model experiments. Every new signal stays advisory; never
  auto-accept.
- Branch `main`; commits are often stacked **locally and unpushed**.
- Data caveat: **new** benchmark runs carry the authoritative `run_kind` field;
  **historical** `var/benchmark/*/bench.db` rows have no field, so their fake/real split
  stays heuristic (`scripts/audit_bench.py`, labeled). Historical data is read-only —
  never backfilled (see `docs/00_foundation/42_AI_TEST_FAILURE_EMPIRICAL_AUDIT.md` §A,
  `docs/50_benchmark/43_RUN_KIND_DESIGN.md`).

## Read first
1. `docs/00_foundation/00_PROJECT_CHARTER.md` — top constraint
2. `docs/00_foundation/40_CORE_THESIS_REPOSITIONING.md` — thesis
3. `docs/00_foundation/42_AI_TEST_FAILURE_EMPIRICAL_AUDIT.md` — real data + §A reproducibility
4. `docs/knowledge/` — agent memory (start at `README.md`): external agent/testgen lessons, benchmark strategy, business-invariant test value. All three converge: **`run_kind` is the critical next step**.
5. `docs/README.md` — doc index

## Toolchain (this machine)
- Python: **use the venv** → `& "E:\AI-Test-Platform\.venv\Scripts\python.exe"`.
  Bare `python` is the Windows Store stub (exits 49, no output).
- Verify command:
  `& "E:\AI-Test-Platform\.venv\Scripts\python.exe" -m pytest` → expect
  `225 passed, 4 skipped` (the count grows as tests are added).

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
- Claude Code: implementation, only after an approved bounded task.
- Claude (research/design): docs/design only, no code unless asked.
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
