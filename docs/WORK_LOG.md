# Work Log — context snapshot for /compact

> Written 2026-06-11, immediately before a planned `/compact`. Snapshot of where the
> project stands so the next session resumes without re-deriving context. Documentation
> only — no code changed.

## 1. Current phase

**Foundation-hardening phase.** Feature/design work is paused. The thread is
trustworthiness + agent-safety, not new features. The `run_kind` **minimal slice is
done**; its **S2 follow-up is deferred (not done)**. The decisions/failures ledger
(`docs/00_foundation/44_DECISIONS_AND_FAILURES.md`) was just written and is **uncommitted,
awaiting the owner's confirmation**.

Project thesis (unchanged): **judge, don't generate.** Generation is one producer; the
product is the judge → quality gate → review → ledger → reproducible-report layer. See
`docs/00_foundation/40_CORE_THESIS_REPOSITIONING.md` and the boundary in `CLAUDE.md`.

## 2. Completed content (this arc)

- **Repositioning**: docs/40 (thesis), Charter sharpened (`46f9485`).
- **Empirical audit + reproducibility correction**: `docs/00_foundation/42_…` — retracted
  "43% green-but-worthless", corrected to real-model **n=67** (§A).
- **Ledger P1 + P2**: `app/ledger/` (models/store/ingest/analytics) — `437983b`, `ac74a84`.
- **Foundation guards** (`e728cf1`): `CLAUDE.md` (agent guide + anti-hallucination
  boundary), `tests/conftest.py` (forces fake provider unless `TESTAGENT_E2E=1`),
  `scripts/audit_bench.py` (read-only benchmark audit).
- **Knowledge base** under `docs/knowledge/` (+ index): `EXTERNAL_AGENT_AND_TESTGEN_KB`,
  `BENCHMARK_SOURCES_AND_STRATEGY`, `INTERNET_TECH_BUSINESS_KB` — `cdce34e`, `4e18445`.
- **`run_kind`**: design `docs/50_benchmark/43_RUN_KIND_DESIGN.md` (`aedd9e6`) + **minimal
  slice** (`0f2d00a`): `app/llm/run_kind.py` (`resolve_run_kind` + guard), plumbed through
  `generate_pipeline` → `BenchCaseResult` → `JudgedRecord`, `run_benchmark --run-kind`
  flag, `audit_bench.py` prefers the field, `tests/test_run_kind.py`.
- **CLAUDE.md fact-correction** (`58b0979`): run_kind moved from PAUSED to Done-minimal-slice.
- **docs/44 decisions/failures ledger**: written, **uncommitted** (this turn).

## 3. Current git status

- Branch `main`, **synced with `origin/main`** (0 ahead). Last pushed: **`58b0979`**.
- **1 untracked file**, uncommitted/unpushed:
  `docs/00_foundation/44_DECISIONS_AND_FAILURES.md`.
- After writing this file, `docs/WORK_LOG.md` will also be untracked.
- Working tree otherwise clean (no modified tracked files).

## 4. Most recent test / verification commands (all PASSED)

Use the **venv** python — bare `python` is the Windows Store stub (exit 49, no output):
`& "E:\AI-Test-Platform\.venv\Scripts\python.exe" …`

- `… -m pytest tests/test_run_kind.py` → **4 passed**
- `… -m pytest tests/test_ledger.py` → **10 passed**
- `… -m pytest -p no:warnings` → **229 passed, 4 skipped** (the 4 skipped are the
  `TESTAGENT_E2E`-gated e2e tests)
- `… scripts/audit_bench.py` → 28 bench.db / 80 rows / **0 authoritative run_kind, 80
  heuristic**; reproduces docs/42 §A (real-heuristic n=67: compile 61% / pass 25% /
  green-FAIL 0/17). No failing commands.

## 5. Next single task

**Finalize `docs/00_foundation/44_DECISIONS_AND_FAILURES.md`**: on the owner's
confirmation, commit it (and `docs/WORK_LOG.md`), then push. Optionally add doc 44 to
`docs/README.md` (left unindexed to keep `git diff --stat` clean). **Do not start
anything else** (no S2/P3/etc.) without explicit approval.

> After that, the next *engineering* step would be **run_kind S2** (default the benchmark
> `aggregate()` and ledger analytics to `run_kind == real`) — but it is **forbidden until
> explicitly approved** (see §6).

## 6. Forbidden modification scope (standing red-lines)

- **No S2** (run_kind query-default), **no P3 / `submit_candidate`**, **no Defects4J**,
  **no multi-model experiments**, **no new features**, **no broad refactor**.
- **No real model / API calls** without explicit owner confirmation (state command + cost first).
- **Never modify benchmark historical data** — `var/benchmark/*/bench.db` is read-only;
  **no backfill**.
- **Never change judging / quality-gate / oracle logic.** Never auto-accept (conclusion
  stays `NEED_HUMAN_REVIEW`, `trusted=False`); never auto-fix oracle (no expected→actual
  rewrite, never weaken/delete assertions).
- **Never edit production code / pom / existing tests** as part of generation.
- **Never read, print, summarize, or commit `.env`.**
- **Push is human-only.** Agents commit locally; never `git push` without approval.

## 7. Key conclusions to retain (must survive compaction)

- **Contamination incident (docs/44, docs/42 §A):** raw `n=80` mixed 13 fake/dry-run
  placeholder jobs (`dryrun1/2/3` + `manifest-dryrun`×10); real-model **n=67**.
- **"43% green-but-worthless" was RETRACTED** — two defects: (a) all those rows were
  fake-client placeholders (`no_assertions`); (b) off-by-one (11 not 12; one was a
  `TEST_FAILURE`, not green). Real subset green-but-FAIL = **0/17**. Project data does
  **not** support "AI green tests are mostly worthless"; semantic oracle strength is
  **not measured** (stays human-review).
- **口径 caveat:** only `gen_outcome` is historical; quality-gate + recommendation are
  **recomputed by current code** over stored sources. compiled strict 61% / loose 66%;
  pass 25%; quality-PASS 24% (real n=67, direction-only, not significant).
- **`run_kind` = {real, fake, dryrun, smoke}** (4 kept distinct). **Invariant: a fake
  client can never produce `real`** (`resolve_run_kind` raises; regression-tested).
  Producer-set at generation time, never reconstructed from artifacts. Historical bench.db
  read-only / no backfill (heuristic fallback allowed, labeled). **Headline model-quality
  metrics default to authoritative `real` only**; fake/dryrun/smoke + unknown → raw/audit.
- **run_kind minimal slice DONE; S2 DEFERRED.**
- **Toolchain:** venv python only; verify = `pytest` (229 passed, 4 skipped); audit =
  `scripts/audit_bench.py`.
- **Read-first for next agent:** `CLAUDE.md`, `docs/00_foundation/{00 charter, 40 thesis,
  42 audit, 44 decisions}`, `docs/knowledge/README.md`, `docs/50_benchmark/43_RUN_KIND_DESIGN.md`.
