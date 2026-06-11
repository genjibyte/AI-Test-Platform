# CLAUDE.md — agent operating guide for TestAgent Lab

> Read this first, every session. Short on purpose. If reality conflicts with this
> file, trust the repo and fix this file.

## Thesis (what this project is)
A **Java/Maven AI unit-test _candidate evaluation & audit_ platform.** Candidate tests
may come from the built-in generator, Claude, Codex, DeepSeek, or a human. The product
is the **judge → quality gate → review recommendation → badcase ledger → reproducible
report** layer. **Generation is just one producer.**
See `docs/00_foundation/40_CORE_THESIS_REPOSITIONING.md` and the charter
`docs/00_foundation/00_PROJECT_CHARTER.md`.
Out of scope: UI automation, API automation, manual test-case generation, generic
RAG / multi-agent platform, enterprise task management.

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

## Current state (2026-06-11)
- Done: judge + minimal generation pipeline; quality gate + review policy (advisory,
  never auto-accept); preflight + oracle-safe compile-repair (gated off); ledger
  P1/P2 (`app/ledger/`).
- **PAUSED — foundation-hardening phase.** All feature/design work is paused,
  including P3 / `submit_candidate`, the `run_kind` schema, and new repair/preflight
  buckets, until foundation hardening is done. Do **not** resume features without
  explicit approval.
- Branch `main`; commits are often stacked **locally and unpushed**.
- Data caveat: historical `var/benchmark/*/bench.db` mixes real + fake/dry-run jobs
  (see `docs/00_foundation/42_AI_TEST_FAILURE_EMPIRICAL_AUDIT.md` §A). **There is no
  `run_kind` field yet.**

## Read first
1. `docs/00_foundation/00_PROJECT_CHARTER.md` — top constraint
2. `docs/00_foundation/40_CORE_THESIS_REPOSITIONING.md` — thesis
3. `docs/00_foundation/42_AI_TEST_FAILURE_EMPIRICAL_AUDIT.md` — real data + §A reproducibility
4. `docs/README.md` — doc index

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
