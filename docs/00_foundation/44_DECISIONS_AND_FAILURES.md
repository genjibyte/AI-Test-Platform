# Decisions & Failures Ledger

> Date: 2026-06-11. **Documentation only** — no code, no tests, no benchmark-data change.
> Durable record of the project's data-contamination incident and the decisions it
> precipitated, so future agents do not repeat it. Cross-refs:
> `docs/00_foundation/42_AI_TEST_FAILURE_EMPIRICAL_AUDIT.md` §A,
> `docs/50_benchmark/43_RUN_KIND_DESIGN.md`, `scripts/audit_bench.py`,
> `tests/test_run_kind.py`, `app/llm/run_kind.py`, `app/llm/fake_client.py`.

This ledger is **not** proof that any feature is complete. It records what failed, why,
how it was corrected, and the rules that prevent recurrence.

---

## F-001 — Fake-client / dry-run / smoke jobs contaminated the headline benchmark sample

**Symptom.** A benchmark "headline" sample of **n=80** generation rows (aggregated across
all `var/benchmark/*/bench.db`) was treated as model-quality evidence. It silently
**mixed real-model runs with non-model jobs**.

**Root cause.** There was **no provenance field** distinguishing real vs fake/dry-run/
smoke runs. The only signals were incidental: the literal `// FAKE CLIENT PLACEHOLDER`
string in `test_source` (emitted by `app/llm/fake_client.py`) or `model == "fake-1"`.
Cross-run aggregation pulled in **13 non-model rows**:

- `dryrun1`, `dryrun2`, `dryrun3` — 1 each (3 total)
- `manifest-dryrun` — 10

→ **13 fake / dry-run jobs out of 80.** The `FakeLLMClient` placeholder compiles and
"passes" (it asserts nothing), so these rows looked like green tests.

**Impact.** Headline rates were inflated/distorted, and at least one published conclusion
was an artifact of the fakes (see F-002).

**Fix.** (a) Corrected the report to the real-model subset (F-003). (b) Made the audit
tool separate fake vs real and print the limitation. (c) Added the authoritative
`run_kind` field so new runs are tagged at the source (D-001..D-005). **Historical data
was not mutated** (D-003).

**Prevention / regression.** `app/llm/run_kind.py` + `tests/test_run_kind.py` (the
invariant in F-005); `scripts/audit_bench.py` prefers the authoritative field and labels
the heuristic fallback; `docs/knowledge/` records the lesson.

**Owner / status.** Owner: human. Status: **contained** — `run_kind` minimal slice done;
the S2 query-default follow-up is deferred (not done).

---

## F-002 — "43% green-but-worthless" conclusion was retracted

**Symptom.** An earlier version of `docs/42` claimed *"of compiled+passed tests, ~43%
(12/28) are quality-FAIL → green-but-worthless."*

**Why it was retracted (two independent defects):**

1. **Contamination (F-001).** All of the "green-but-quality-FAIL" rows were
   **fake-client placeholders** (`manifest-dryrun` ×10 + `dryrun3` ×1), which fail the
   quality gate on `no_assertions` because the placeholder asserts nothing. They are not
   real model output. In the **real-model subset, green-but-quality-FAIL = 0/17.**
2. **Arithmetic / cross-tab error.** The figure conflated marginals. The quality-FAIL
   count over compiled+ran rows was 12, but **one of those 12 was a `TEST_FAILURE`, not a
   green (PASS-execution) test**. The correct green-but-FAIL count on the raw set is
   **11/28**, not 12/28 — and on the real set it is **0**.

**Corrected statement.** The project's own real data does **not** support "AI green tests
are mostly worthless." Structural quality (assertion presence/strength) is judged by the
gate; **semantic oracle strength is not measured** and remains `NEED_HUMAN_REVIEW`.

**Prevention.** Distinguish carefully: *green / PASS-execution* ≠ *quality-FAIL*; a
quality-FAIL row may be a `TEST_FAILURE`. Always reproduce a cross-tab from raw before
publishing (see F-008 rules).

**Owner / status.** Owner: human. Status: **retracted & corrected** in `docs/42` §A.

---

## F-003 — Corrected real-model sample (n=67) and its measurement criteria (口径)

After removing the 13 fake/dry-run placeholders: **real-model n = 67.**

**Definitions (口径) — read before quoting any number:**

| metric | definition | provenance |
|---|---|---|
| `gen_outcome` | the stored `execution.gen_outcome` (PASS / TEST_FAILURE / COMPILE_FAILURE / …) | **historical fact** (recorded at run time) |
| compiled | `gen_outcome ∈ {PASS, TEST_FAILURE, NO_TESTS}` (strict, platform `_COMPILED`); "loose" = not `COMPILE_FAILURE` | derived |
| passed | `gen_outcome == PASS` | derived |
| quality-gate | `evaluate_test_quality(...)` status (PASS / REVIEW / FAIL) | **recomputed** by current code over the stored source |
| recommendation | `recommend_with_reasons(...)` incl. risk-aware downgrade | **recomputed** by current code (not the label emitted then) |

> Critical caveat: **only `gen_outcome` is historical**; quality-gate and recommendation
> are *replayed* with today's judging logic over the stored sources. So e.g. "STRONG = 0"
> is "today's standard looking back," not the label at the time.

**Real-subset headline (n=67), heuristic provenance:** compiled (strict) 61% (loose 66%);
passed 25%; quality-gate PASS 24%; **green-but-quality-FAIL = 0/17**. These are
**direction-only** (n=67 across heterogeneous configs, mostly single-sample), not
statistically significant. Reproduce with `scripts/audit_bench.py` (read-only).

---

## D-001 — `run_kind` has four kinds: real / fake / dryrun / smoke

A generated-test candidate is tagged at generation time with exactly one of:

- **real** — produced by a real provider/model. **The only kind allowed in headline
  model-quality metrics.**
- **fake** — `FakeLLMClient` placeholder output (contracts-only, asserts nothing).
- **dryrun** — fake client deliberately run on real repos to exercise the harness.
- **smoke** — tiny harness check (e.g. `samples/calc`).

The four kinds are kept **distinct**; `dryrun`/`smoke` are **not** merged into `fake`.
(`app/llm/run_kind.py: RUN_KINDS`.)

---

## D-002 — Invariant: a fake client can never produce `real`

This is the load-bearing anti-contamination rule and is **regression-tested**:
`resolve_run_kind(client_is_fake=True, override="real")` **raises** `ValueError`
(`app/llm/run_kind.py`, `tests/test_run_kind.py`). `run_kind` is decided by the
**producer at generation time** and is **never reconstructed from artifacts or source
text** in the pipeline.

---

## D-003 — Historical `bench.db` is read-only; no backfill

Historical benchmark databases are **never mutated or backfilled** with `run_kind`. They
have no field → they are **unknown**. `scripts/audit_bench.py` may use a **heuristic
fallback** for unknown rows (`FAKE CLIENT PLACEHOLDER` / `model == "fake-1"`) but **must
label it** as heuristic / non-authoritative and incomplete. New runs carry the
authoritative field going forward.

---

## D-004 — Headline model-quality metrics default to authoritative `real` only

Headline metrics use **`run_kind == "real"` (authoritative) only**. `fake` / `dryrun` /
`smoke` and `unknown` (historical) rows are **raw / audit counts**, shown separately and
clearly labeled — never folded into model-quality claims. (Today `audit_bench.py`
enforces this; defaulting the benchmark `aggregate()` and ledger analytics to `real` is
the deferred S2 follow-up.)

---

## R — Anti-error rules for future agents (derived from this incident)

1. **Never present `fake` / `dryrun` / `smoke` output as model-quality evidence.** The
   `FakeLLMClient` placeholder is not a real test.
2. **Headline = authoritative `real` only.** Never compute a model-quality rate over a
   mixed-`run_kind` set. Show raw vs real separately.
3. **Keep the invariant.** A fake client can never be `real` (`resolve_run_kind` guard +
   its regression test). Do not weaken or remove that test.
4. **Never reconstruct `run_kind` from artifacts/source in the pipeline.** Only the audit
   tool's historical fallback may infer, and it must say so.
5. **Never backfill or mutate historical `bench.db`.** Treat historical data as read-only;
   unknown stays unknown.
6. **Reproduce before you publish.** Every headline number must be regenerable from raw
   via `scripts/audit_bench.py`. No hand-computed numbers in conclusions.
7. **Mind the cross-tab.** Distinguish *green / PASS-execution* from *quality-FAIL*; a
   quality-FAIL row can be a `TEST_FAILURE`, not a green test. Off-by-one here caused F-002.
8. **Disclose recompute provenance.** Only `gen_outcome` is historical; quality-gate and
   recommendation are replayed by current code — say so when quoting them.
9. **Green ≠ useful; coverage-up ≠ correct.** Structural quality is gated; **semantic
   oracle strength is not measured** and stays `NEED_HUMAN_REVIEW`. Do not overclaim
   bug-detection ability.
10. **Evidence rule.** No success/finding claim without the command + its output.

---

> This ledger records facts and decisions only. It grants no new scope. The project stays:
> *AI-generated test candidate evaluation / audit / engineering-usability platform.*
