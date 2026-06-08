# Compile-Only Repair — Enablement Plan (Design)

> Date: 2026-06-08. **Design only. NOT acted on.** No code change, no model run, no
> new benchmark in this document. It defines *how* the deterministic compile-only
> repair (`app/repair/compile_repair.py`) could be turned on safely, the gates it
> must clear first, and the success/rollback criteria. Decision points for the user
> are in §7.
>
> Precondition met: the repair is now oracle-safe **by construction** for its only
> oracle-risk bucket (docs/38 §7.1 — `List.of` rewrite confined to `= List.of`
> initializer position). This is the stable point this plan builds on.

## 0. Where we are

- Repair is **gated off**: `Settings.repair_compile_failures = False`
  (`app/config.py:49`), `repair_max_rounds = 1` (`:50`). The benchmark runner wires
  these through verbatim (`app/benchmark/runner.py:221-222`); nothing in Phase 2/2.5
  enables repair today.
- Repair is **deterministic, model-free**, three buckets only:
  `missing_static_import` (log-triggered), `method_local_type` (enum hoist),
  `java_source_level` (`List.of`→`Arrays.asList`, initializer-only).
- Repair **never declares a test fixed**: it re-runs Maven after each round and
  Maven stays the compile verifier (docs/07 A2). Conclusion stays
  `NEED_HUMAN_REVIEW`, `trusted=False` regardless (Phase 4 policy).
- Offline replay over all `bench.db` (docs/38 §7.1): oracle-touch **0**;
  `List.of` bucket is **dormant** on the historical corpus; only
  `missing_static_import` fixes a real case (`assertNotEquals`-not-imported).

So enabling repair is **low-upside, low-risk** on today's evidence: it would fix a
narrow minority of compile failures (imports/enums) and touch no oracle. The
question this plan answers is whether the upside is worth turning on, and under what
guard rails.

## 1. What "enable" means

Exactly one change at enablement time: set `repair_compile_failures=true` (env
`TESTAGENT_REPAIR_COMPILE_FAILURES`) for the chosen run(s), keeping
`repair_max_rounds=1`. **No source change is required to enable** — the wiring
already exists. Rollback is the same switch back to `false` (§4).

### Bucket tiering (no new buckets)

| bucket | oracle risk | corpus effect | enable? |
|---|---|---|---|
| `missing_static_import` (log-triggered) | none (inserts import lines) | fixes 1 real case | **yes** |
| `method_local_type` (enum hoist) | none (moves helper enums) | 2 historical hoists | **yes** |
| `java_source_level` (`List.of`, initializer-only) | none by construction (docs/38 §7.1) | dormant (0) | **yes, kept conservative** |

Explicitly **out of scope** (do not add to enable repair): generics/wildcard repair,
receiver-type repair, overload-cast repair, and anything that edits an assertion
body. These were the dominant *unrepaired* compile buckets (docs/38 §2) and adding
them is a separate, later decision — not part of this enablement.

## 2. Validation gates (each must pass before the next)

**Gate 0 — Offline oracle-safety (DONE).** docs/38 §7.1: 23 `COMPILE_FAILURE`
samples replayed at Java 8 (worst case); in-assertion `List.of` rewritten = 0; full
suite 201 passed. ✔

**Gate 1 — Offline repair-diff replay (no model, can run now).** For every historical
`COMPILE_FAILURE` test source, apply `repair_compile_failure` with each repo's real
`java_source_level` and real compile log, and assert: (a) every diff is import-line
insertion, enum hoist, or a non-assertion `= List.of` rewrite — never an edit inside
an `assert…`/matcher argument; (b) repair output still requires a Maven re-run (the
loop never sets a passed/trusted flag). This is a stricter, log-accurate version of
Gate 0 and stays zero-cost. *Deliverable: a short appendix to docs/38 or a docs/40
note; still no enablement.*

**Gate 2 — Small live A/B (REQUIRES EXPLICIT USER CONFIRMATION — model run + cost).**
Pick targets that actually *exercise* a repair bucket (not the frozen cases, where
repair is a no-op). Best candidate from history: the v3_2_3 `Option` run whose only
failure was a missing `assertNotEquals` static import (`missing_static_import`
territory). Run repair **OFF vs ON** on a 2–3 case subset, same pinned commits, pro
model. Compare:

- compile-pass rate (expect ON ≥ OFF on the import-failure case),
- gen-test pass rate (must not regress),
- **oracle-touch = 0** (assert by diffing every generated vs final test source),
- `trusted` stays `False`, conclusion stays `NEED_HUMAN_REVIEW`,
- `production_code_touched = False`,
- `repair_rounds ≤ 1`.

Estimated cost: ~4–6 pro generations (2–3 cases × {OFF, ON}). **I will state the exact
command, case list, and token/cost estimate and wait for go-ahead before running
anything** (standing red-line: no real-model run without explicit confirmation).

## 3. Success criteria (to keep repair on)

Repair stays enabled only if, on Gate 2:
1. oracle-touch = 0 (hard gate — any violation reverts immediately);
2. no `trusted=True`, no auto-accept, conclusion always `NEED_HUMAN_REVIEW`;
3. no production/pom/existing-test modification;
4. compile-pass rate strictly improves on ≥1 case and **regresses on none**;
5. gen-test pass rate does not regress;
6. `repair_rounds` bounded by `repair_max_rounds` (1).

If 1–3 ever fail → red-line breach → revert and re-audit. If 4–5 show no benefit →
repair is harmless but pointless; leave it **off** and record the negative result
(don't carry dead complexity into the default path).

## 4. Rollback

Single switch: `TESTAGENT_REPAIR_COMPILE_FAILURES=false` (the default). No schema, no
data, no source revert needed. Because repair only ever *adds* compile-fix attempts
before a mandatory Maven re-verify, disabling it returns the pipeline to exact
Phase 2/2.5 behavior. Rollback is therefore zero-risk and instantaneous.

## 5. Observability (already in the report; confirm before enabling)

`assemble_generation_report` already surfaces `repair.repair_rounds`,
`repair.final_outcome`, and `repair.enabled`; the benchmark records `repair_rounds`
and `repair_final_outcome` per case (`app/benchmark/runner.py:186-187`). Before
enabling, confirm the per-case report also lists the applied **patch buckets** so a
reviewer can see *what* repair changed (the `RepairPatch.bucket/description` are
produced but should be carried into the report/JSON for the live A/B). This is the
only small reporting addition the plan may need — to be decided at Gate 2, not now.

## 6. Red lines / non-goals (unchanged)

- Never auto-accept; never auto-fix oracle (no expected→actual rewrite, no
  weakening/deleting assertions). Repair edits only imports, helper enums, and
  non-assertion `= List.of` initializers.
- No new repair buckets to enable (generics/receiver/overload-cast stay out).
- Maven remains the verifier; no repaired test is trusted without re-compilation.
- Coverage-subset restoration is a **separate** roadmap item (still deferred); not
  bundled into repair enablement.
- API keys never logged/committed; no production code/pom/existing tests touched.

## 7. Open decisions for the user

1. **Do Gate 1 now?** (offline, zero-cost, strengthens evidence) — recommended yes.
2. **Authorize Gate 2 live A/B?** (4–6 pro generations; I will quote exact command +
   cost first) — needed to decide if the import/enum fixes are worth keeping on.
3. **Default posture if Gate 2 shows benefit only on import failures:** enable repair
   by default, or keep it opt-in per run? (Recommendation: keep **opt-in** until a
   larger benchmark justifies a default flip — consistent with the conservative,
   judge-first stance.)

> This document is design only. No code, model, benchmark, or default was changed by
> writing it.
