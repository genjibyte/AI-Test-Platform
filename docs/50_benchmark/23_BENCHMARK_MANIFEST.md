# Phase 2.6 — Frozen Benchmark Manifest (v1) + value-judgment enrichment (v2)

> Date: 2026-06-07 (v1); enriched 2026-06-20 (v2). Nature: **measurement instrument**.
> This is the benchmark we hold fixed so context/model changes can be compared apples-to-apples.
> Upstream: `docs/14` (Phase 2.5 benchmark), `docs/21` (pro quality run), `docs/22` (review policy).
> Boundary (user roadmap step 2): build the manifest, **freeze the 3 cases, expand to 8–12**. No model run here.
> **v2 (§5):** same 10 pins, ENRICHED with business-invariant tags (docs/45) + anchoring
> invariant descriptors (docs/48). See `benchmarks/manifest.v2.json`.

---

## 0. Why a manifest (vs `spec.example.json`)

`benchmarks/spec.example.json` cloned each repo at **whatever HEAD was current**, so
re-running it later tests *different code* — the benchmark drifts and v2-vs-v3
comparison is confounded. A benchmark used to measure progress must be **frozen**.

`benchmarks/manifest.v1.json` pins **every case to an exact commit SHA**. Re-running
it next month, on another machine, or against a new context version exercises the
*same code* every time.

---

## 1. Pinning strategy (reproducible, zero-cost baseline reuse)

- **Every case carries `commit`** — a full 40-hex SHA. The harness fetches that
  exact revision (`app/benchmark/runner.py::_ensure_mirror`): `git init` →
  `git fetch --depth 1 <url> <sha>` → `git checkout -b pinned FETCH_HEAD`. The
  mirror's default branch (`pinned`) is the pinned commit, so the per-job clone
  the importer does checks out exactly that SHA. `commit` is part of the mirror
  cache key, so two pins on one repo get distinct mirrors.
- **The 3 baseline cases are pinned to the EXACT commits `var/benchmark/v2-pro-quality-final` ran on**
  (Option `ae44dcd`, CSVRecord `8192d9d`, WordUtils `e910b53`). Consequence: that
  pro run **stays a valid v2 data point with zero model re-run** — step 4 only
  needs to spend budget on v3.
- `ref` is a human label for the pin (tag name or "frozen: …"); advisory only.
- Coverage stays **advisory** (`-Djacoco.skip=true`, see §4) — not part of the freeze.

A new `commit` (and optional `ref`) field was added to `BenchCase`; the change is
isolated to the benchmark mirror logic and does **not** touch the Phase 2 generate
flow. Offline tests: `tests/test_benchmark_manifest.py` (manifest shape + the
commit-pin mechanism against a local two-commit repo).

---

## 2. Cases (10 across 4 repos)

All Apache Commons (known-buildable, single-module JUnit5 Maven). Whole-class
targets (no method) avoid signature guesswork. Buckets are the failure dimensions
**Context v3 (step 3) targets**.

| # | case | target | bucket | frozen baseline? |
|---|---|---|---|---|
| 1 | commons-cli Option | `o.a.c.cli.Option` | api-contract | ✅ v2-pro-quality-final |
| 2 | commons-cli Options | `o.a.c.cli.Options` | api-contract | — |
| 3 | commons-cli CommandLine | `o.a.c.cli.CommandLine` | exception-semantics | — |
| 4 | commons-csv CSVRecord | `o.a.c.csv.CSVRecord` | exception-semantics | ✅ v2-pro-quality-final |
| 5 | commons-csv CSVFormat | `o.a.c.csv.CSVFormat` | exception-semantics | — |
| 6 | commons-text WordUtils | `o.a.c.text.WordUtils` | pure-function | ✅ v2-pro-quality-final |
| 7 | commons-text StringEscapeUtils | `o.a.c.text.StringEscapeUtils` | pure-function | — |
| 8 | commons-lang3 NumberUtils | `o.a.c.lang3.math.NumberUtils` | exception-semantics | — |
| 9 | commons-lang3 Validate | `o.a.c.lang3.Validate` | exception-semantics | — |
| 10 | commons-lang3 BooleanUtils | `o.a.c.lang3.BooleanUtils` | pure-function | — |

Revisions: cli `ae44dcd`, csv `8192d9d`, text `e910b53` (the v2 baseline HEADs);
lang `598dfc1` = `rel/commons-lang-3.20.0` (a clean release tag, no prior baseline).

**Bucket balance** (deliberate): exception-semantics ×5, pure-function ×3,
api-contract ×2. The exception-semantics cases are where pro v2 failed in
`docs/21` (CSVRecord guessed the wrong exception type; Option misused an internal
API). They are exactly what v3 grounding must move from `TEST_FAILURE`/`NEEDS_REVISION`
toward `STRONG_REVIEW_CANDIDATE`. The pure-function cases are PASS baselines that
must **not** regress.

---

## 3. How step 4 uses it

- Run the manifest through **v3 context + deepseek pro** → `var/benchmark/v3-pro`.
- **Controlled delta** on the 3 frozen cases: v2 = `v2-pro-quality-final` (same
  exact commits, no re-run) vs v3 = the new run. Compare `gen_outcome`,
  `quality_gate_status`, `review_recommendation`, and the expected/actual the
  review summary extracts (docs/22).
- **Broader coverage** on the other 7: absolute v3 performance across the buckets.
- Headline metrics: `gen_test_pass_rate`, `recommendation_distribution`,
  `top_failure_types`. Red-line unchanged: `conclusion` stays `NEED_HUMAN_REVIEW`.

Step 4 spends model budget → **requires explicit user confirmation** (command +
cost + expectation stated first).

---

## 4. Reproducibility & run commands

Skip the policy plugins + the conflicting JaCoCo agent (docs/14 F1/F2); coverage
is advisory and reported `unavailable`:

```powershell
$env:TESTAGENT_MVN_EXTRA_ARGS='-Drat.skip=true -Dcheckstyle.skip=true -Dspotbugs.skip=true -Dlicense.skip=true -Denforcer.skip=true -Danimal.sniffer.skip=true -Dmaven.javadoc.skip=true -Dpmd.skip=true -Djacoco.skip=true'

# offline dry-run (fake client, no model, no key) — buildability + target resolution:
$env:TESTAGENT_LLM_PROVIDER='fake'
.\.venv\Scripts\python.exe -m scripts.run_benchmark benchmarks\manifest.v1.json --out var\benchmark\manifest-dryrun

# formal v3 run (real model — needs confirmation; step 4):
$env:TESTAGENT_LLM_PROVIDER='deepseek'; $env:TESTAGENT_LLM_MODEL='deepseek-v4-pro'; $env:TESTAGENT_LLM_API_KEY='...'
.\.venv\Scripts\python.exe -m scripts.run_benchmark benchmarks\manifest.v1.json --out var\benchmark\v3-pro
```

---

## 5. Boundaries (explicitly not doing)

- No model run in step 2; the dry-run is offline (fake client).
- No expansion beyond 12 cases this round; no new repo families until cli/csv/text/lang are proven stable.
- No coverage gate (that is roadmap step 6, on a JaCoCo-conflict-free subset).
- Manifest is **frozen**: changing a pin = a new manifest version (`manifest.v2.json`), never an in-place edit.

---

## 6. Validation status (offline, zero model cost)

- Unit: `tests/test_benchmark_manifest.py` — manifest loads, 10 cases, all SHA-pinned,
  3 frozen cases match the exact baseline commits, 4 distinct repo revisions, and the
  commit-pin mirror+clone yields the pinned SHA (not the tip). Full suite: **164 passed, 4 skipped**.
- Offline dry-run (fake client) on all 10 cases completed at
  `var/benchmark/manifest-dryrun` (zero model cost):
  - `total_cases=10`, `repos=4`, `buildable_repos=4`, `generation_attempted=10`
  - `setup_failures=0`, `clone_failures=0`, `repo_build_failures=0`
  - `compile_pass_rate=100%`, `gen_test_pass_rate=100%`
  - `coverage_measured=0/10` because the dry-run intentionally used
    `-Djacoco.skip=true`
  - `quality_gate_pass_rate=0%`, `quality_gate_failures=10`,
    `recommendation_distribution={REJECT_CANDIDATE: 10}`
  - slowest bucket: commons-lang3 (`NumberUtils`, `Validate`, `BooleanUtils`)
    at about 8.7-9.2 minutes per case, because the current judge/generate flow
    runs the full Maven test suite for each target

Interpretation: the dry-run proves the frozen manifest is operational for
clone/build/judge/target-resolution/generate/execute/report across all 10 cases.
It does **not** prove model quality: the fake client produces placeholder tests,
so the quality gate correctly rejects every generated test. This is acceptable
for Step 2 and is exactly why Step 4 must use a real model only after explicit
confirmation.

<!-- DRYRUN_RESULT -->

---

## 5. v2 — value-judgment enrichment (2026-06-20)

`benchmarks/manifest.v2.json` is **v1's exact 10 pins** (identical `repo_url`+`commit`+
`target_class` → identical code-under-test) plus the **value-judgment dimension** that v1
left empty:

- **Business-invariant tags (docs/45 S1):** `business_domain` / `business_pattern` /
  `risk_level` / `expected_invariant` on every case (controlled vocab, advisory).
- **Anchoring invariant descriptors (docs/48):** 1–2 `InvariantDescriptor`s per case with
  `source="manifest"` (→ anchoring, may drive real verification), `kind`
  (exception/boundary/state_transition), `target_method`, `statement`, `observable`.
  **Method-scoped, no `target_lines`** — exact line numbers can't be pinned offline, and
  method scope is enough for the `docs/48 _scope` reachability check and `docs/49` survivor
  classification.

**Why a new file, not an edit to v1:** v1 stays the frozen reproducibility pin (its
`v2-pro-quality-final` baseline comparison is untouched). v2 only adds **advisory** metadata
— it changes no verdict (`conclusion` stays `NEED_HUMAN_REVIEW`, `auto_accept` blocked). The
statements are **grounded** in the documented behavior captured in
`docs/60_context_v3/CONTEXT_V3_EVOLUTION_DIGEST.md` (e.g. `Option.addValue` always throws;
`Option.getValues()` returns `null` not `[]`; `CSVRecord.get` throws on bad key/index;
`Validate.notNull`→NPE / `isTrue`→IAE).

**What v2 activates** that v1 left dormant for the benchmark: the docs/45 business rubric, the
docs/48 invariant-verification view (`asserted`/`addressed`/`pinned`), docs/49 scoped survivor
classification, and the digest's invariant flags — all advisory. Running v2 with gated PIT
(`mutation_enabled`) lets an anchoring invariant reach `pinned` when its method-scoped mutants
are all killed. Validated offline by `tests/test_benchmark_manifest_v2.py` (loads; v2 pins ==
v1 pins; every case has known tags + anchoring, method-scoped invariants; the verifier never
accepts).

**Next enrichment (breadth, deferred):** adding NEW (repo, commit, target) cases needs commit
SHAs verified against the real repos — not inventable offline — so it stays a separate,
network-gated step. v2 enriches **depth** (the verifiable, on-thesis move) now.
