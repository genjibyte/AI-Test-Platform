# P1-T3 `run_kind` — design

> Date: 2026-06-11. **Design only. NOT implemented.** No code, no model, no benchmark,
> no data mutation. Foundation-hardening phase; `run_kind` implementation stays paused
> until explicit approval. This doc locks down *what* to build so the eventual change
> is small, bounded, and reviewable.
>
> Upstream: docs/42 §A (contamination incident), `scripts/audit_bench.py` (current
> heuristic + LIMITATION), `docs/knowledge/` (all three KBs name `run_kind` the
> critical next step), audit finding **F-001 (Blocker)**.

## 0. Why

Fake/real separation is currently **heuristic and unenforced**: the only signals are the
literal `// FAKE CLIENT PLACEHOLDER` string in `test_source` (`app/llm/fake_client.py`)
or `model == "fake-1"`. There is **no schema field** and **no regression test**, so
headline metrics can be silently contaminated — which already happened (n=80 raw → 13
fake → n=67 real, docs/42 §A). Goal: one **authoritative** field so headline/ledger
metrics default to real, plus a regression test that prevents recurrence.

## 1. The field

```
run_kind ∈ { real, fake, dryrun, smoke }
```

- **real** — produced by a real provider/model (the only kind allowed in headline
  model-quality metrics).
- **fake** — `FakeLLMClient` placeholder output.
- **dryrun** — fake client deliberately run on real repos to exercise the harness.
- **smoke** — tiny harness check (e.g. `samples/calc`).

`dryrun`/`smoke` are **intent** sub-kinds of "not real"; they cannot be auto-derived
from the client alone.

## 2. Where it is set (single source of truth)

**Decided by the producer at generation time — never reconstructed from artifacts later.**

- **Auto base from the client**: `real` iff the provider is not `fake` **and** the model
  is not `fake-1`; otherwise `fake`. Derive once at run start (benchmark runner /
  `run_generation` entry), from the chosen client/settings — *not* from source text.
- **Intent override**: `scripts/run_benchmark.py` gains `--run-kind {real,fake,dryrun,smoke}`
  (and/or infers `dryrun`/`smoke` from the out-dir label). The flag sets `dryrun`/`smoke`.
- **Hard guard (the anti-contamination invariant)**: a **fake client can never yield
  `real`**. If the client is fake, `run_kind ∈ {fake,dryrun,smoke}`; if the client is
  real, `run_kind = real` unless explicitly overridden to a test-only kind. This guard is
  the thing the regression test pins.

## 3. How it threads (read-only carry — no judging change)

One optional field, copied forward, touching no compile/quality/review logic:

- `generation["run_kind"]` — set in the benchmark runner / `run_generation` (default
  derived; optional param).
- `BenchCaseResult.run_kind: Optional[str]` (`app/benchmark/models.py`).
- `JudgedRecord.run_kind: Optional[str]` (`app/ledger/models.py`); `record_from_bench_case`
  copies it.
- `assemble_generation_report` passes it through read-only.

No change to `gen_outcome`, quality gate, review policy, preflight, or repair.

## 4. Default queries (headline = real)

- `aggregate()` (`app/benchmark/models.py`), `report_md`, and ledger analytics
  (`author_profile` / `aggregate_badcases` / `ledger_summary`) **default to
  `run_kind == "real"`** for headline model-quality numbers; **raw** (all kinds) shown
  separately and clearly labeled.
- `scripts/audit_bench.py`: **prefer the schema field when present**; for historical rows
  that lack it, fall back to the existing heuristic and **say so per the split** (already
  prints the LIMITATION; keep that until all rows carry the field).

## 5. Backward compatibility (historical data)

- Historical `bench.db` rows have no `run_kind` → treat as **unknown**.
- `audit_bench.py` keeps the heuristic for unknown rows and labels the split heuristic /
  incomplete (as today). New runs carry the authoritative field.
- **Do not mutate historical raw artifacts** (KB rule). No in-place backfill of `bench.db`.

## 6. Regression test (closes the recurrence gap)

- A `fake`/`dryrun`/`smoke` row is **excluded** from the real-only headline aggregate and
  from the real `aggregate_badcases` view.
- The **guard** holds: a fake client cannot produce `run_kind == "real"`.

## 7. Scope guard — what NOT to do

- No judging-logic change; no new repair/preflight buckets; no P3 / `submit_candidate`.
- No business-domain tags (`business_domain`/`business_pattern`/`expected_invariant` from
  `INTERNET_TECH_BUSINESS_KB.md`) — that is a **separate, later** field set.
- No model run; no historical-data mutation; small diff.
- The pipeline must not infer `run_kind` from source text; only `audit_bench.py`'s
  historical fallback may, and it must label it.

## 8. Files likely touched (when implemented — NOT now)

- `app/llm/client.py` (or a tiny helper): derive base `run_kind` from a client/settings.
- `app/benchmark/runner.py` and/or `app/pipeline/generate_pipeline.py`: set
  `generation["run_kind"]`.
- `app/benchmark/models.py`: `BenchCaseResult.run_kind` + `aggregate()` real-default + raw.
- `app/benchmark/report_md.py`: real vs raw rows.
- `app/ledger/{models,ingest,analytics}.py`: `JudgedRecord.run_kind` + real-default views.
- `scripts/run_benchmark.py`: `--run-kind` flag.
- `scripts/audit_bench.py`: prefer schema field; label heuristic fallback.
- `tests/`: regression tests (§6).

## 9. Acceptance (when implemented)

- `pytest` green incl. the new regression tests.
- `audit_bench.py` on historical data still works (heuristic, labeled); on a new fake run,
  the schema field is used and the fake row is excluded from real headline.
- A fake row can never appear as `real`.
- No judging change: `conclusion`/`trusted` unchanged; the real-subset numbers match
  today's heuristic-real subset (compile 61% / pass 25% / quality-PASS 24% / green-FAIL
  0/17, docs/42 §A) — i.e. the field formalizes what the heuristic already showed.

## 10. Rollout (small, independently testable slices)

- **S1 — schema + set + carry**: add the field, set it at run start, thread read-only.
  No query change yet.
- **S2 — queries**: aggregate / analytics / report default to real; `audit_bench.py`
  prefers the field.
- **S3 — guard + regression test + `--run-kind` flag**.

Each slice is small and paused until approved.

## 11. Open decisions for the owner

1. Keep all four kinds, or collapse `dryrun`/`smoke` into `fake` + a free-text label?
   (Recommend: keep four; auto only `real`/`fake`; flag/label for `dryrun`/`smoke`.)
2. One-time `run_kind` backfill for historical `bench.db` via a **sidecar** file (never
   mutating raw)? (Recommend: **no backfill**; the audit fallback already handles it.)
3. Set the field in the **benchmark runner** (for benchmark runs) with
   `generate_pipeline` taking an optional `run_kind` param defaulting to derived?
   (Recommend: yes — producer-owned, minimal surface.)

## 12. Decisions confirmed + minimal slice implemented (2026-06-11)

Owner confirmed §11: (1) keep all four kinds, `dryrun`/`smoke` **not** merged into `fake`,
headline = `real` only; (2) **no** historical backfill, historical `bench.db` read-only,
audit keeps a **labeled** heuristic fallback; (3) the producer sets `run_kind` at
generation time, `generate_pipeline` takes an optional param but **never** infers from
artifacts/source, and **"a fake client can never produce `real`" is a regression-tested
invariant**.

**Implemented (minimal effective slice):**
- `app/llm/run_kind.py` — `RUN_KINDS` + `resolve_run_kind(client_is_fake, override)` with
  the guard (override `real` on a fake client raises).
- `app/pipeline/generate_pipeline.py` — optional `run_kind` param; sets
  `bundle["run_kind"]` from the resolved client at the GENERATE step (never from source).
- `app/benchmark/{runner,models}.py` — `run_benchmark`/`run_case` thread an optional
  override; `BenchCaseResult.run_kind`; `_completed_result` stamps it from the bundle.
- `app/ledger/{models,ingest}.py` — `JudgedRecord.run_kind`, copied on ingest.
- `scripts/run_benchmark.py` — `--run-kind {real,fake,dryrun,smoke}` flag.
- `scripts/audit_bench.py` — prefers the authoritative field; **HEADLINE = real only**;
  labeled heuristic fallback for historical rows; never mutates `bench.db`.
- `tests/test_run_kind.py` — the invariant (fake → never `real`), override validation,
  ledger carry.

Validation: full suite **229 passed, 4 skipped**; `audit_bench.py` on historical data
reports `0 authoritative / 80 heuristic` and reproduces docs/42 §A under the clearly-
labeled "historical fallback" view (real-heuristic n=67: compile 61% / pass 25% /
green-FAIL 0/17).

**S2 — implemented (filter-only, 2026-06-12, branch `feat/run-kind-s2`).** `aggregate()`
and the ledger analytics (`aggregate_badcases` / `author_profile` / `ledger_summary`)
gained an optional keyword-only `run_kind` filter; headline views default to
`run_kind == "real"`, with `fake`/`dryrun`/`smoke` and historical `None` (unknown) rows
excluded. Default `None` keeps the raw all-kinds view (back-compat), and `report_md`
renders RAW + HEADLINE(real) side by side. Pure read/filter — no judging/quality-gate/
oracle change; `audit_bench.py` and the "fake can never be real" invariant untouched.
Acceptance: full suite green (231 passed, 4 e2e skipped) + new regression tests in
`test_benchmark.py` / `test_ledger.py`; `audit_bench.py` still reproduces docs/42 §A.
No P3, no Defects4J, no multi-model.

> The companion `DECISIONS_AND_FAILURES.md` (P1-T5) should record the contamination
> incident this field prevents.
