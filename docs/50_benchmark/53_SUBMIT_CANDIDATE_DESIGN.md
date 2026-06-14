# 53 — submit_candidate: judge any producer (design, 2026-06-14)

> **Status: S1 + S2 implemented (2026-06-15); S3 designed, not started.** Closes the
> *"judge candidates from ANY producer"* gap implied by the charter (`docs/00_foundation/00_PROJECT_CHARTER.md`)
> and the thesis repositioning (`docs/00_foundation/40_CORE_THESIS_REPOSITIONING.md`).
> Every signal already on the platform is reused verbatim; no new judging logic, no new
> recommendation logic. Verdict invariants are HARD-CODED at the entry point: `trusted=False`,
> `conclusion="NEED_HUMAN_REVIEW"`, `auto_accept_blocked=True`. A `producer_id` is a *manifest*
> (caller's word), never a warrant.

## 0. Why

The charter is explicit: *"Candidate tests may come from the built-in generator, Claude,
Codex, DeepSeek, or a human. The product is the judge → quality gate → review
recommendation → badcase ledger → reproducible report layer. **Generation is just one
producer.**"* But today the only *entry point* into the judge layer is
`POST /jobs/{id}/generate` — the built-in generator pipeline. There is no way to feed an
externally-produced candidate (a test written by Claude in another session, a test pasted
from Codex CLI, a hand-written test) into the same judge → gate → digest stack.

Consequence: the "producer-agnostic" half of the thesis is currently *claimed but
untestable*. `submit_candidate` is the **smallest endpoint** that makes it true.

This is NOT a generation feature. It is a judge-side entry point. No code is written by
the platform; the candidate source is supplied by the caller.

## 1. What — one endpoint, one new pipeline path, zero new judging logic

```
POST /jobs/{job_id}/submit_candidate
  body: {
    target_class:  string (required)
    target_method: string | null
    test_source:   string (required, raw Java)
    producer_id:   string (required, e.g. "claude-4-7", "codex-cli@2026-06-12", "human:wenchao")
    producer_meta: dict   (optional, free-form caller-declared provenance)
    invariants:    list[dict] (optional, docs/48 InvariantDescriptor shapes)
  }
```

Result: the same `Job` shape today's `/generate` returns, with `job.generation = <bundle>`.
The caller then retrieves the same report via `GET /jobs/{job_id}/generation` —
`assemble_generation_report(bundle)` is **reused untouched**.

### 1.1 What changes inside the pipeline

A new orchestrator `run_external_candidate(job, repo, ...)` that walks
**DONE → TARGET_SELECT → CONTEXT → SUBMIT_EXECUTE → COMPARE → SUBMIT_DONE**.
The two states absent vs `run_generation` are **GENERATE** (no LLM call) and **GEN_EXECUTE**
(replaced by `SUBMIT_EXECUTE` — same Maven runner; different state name so audit trails
don't mix producers).

`SUBMIT_EXECUTE` reuses:
- `resolve_target(...)` from `app.targeting.target_selector`
- `build_snapshot(...)` from `app.context.context_collector`
- `evaluate_generated_test_preflight(...)` from `app.quality.generated_test_preflight`
- `write_generated_test(...)` from `app.generate.test_writer` (rename guard included)
- `execute_generated_test(...)` from `app.generate.gen_executor`
- `compare(...)` from `app.coverage.coverage_compare`

No part of the judge stack — `assemble_generation_report`, `build_review_summary`,
`evaluate_test_quality`, `estimate_oracle_strength`, `detect_mock_smells`,
`build_review_digest` — is touched.

## 2. Bundle shape (delta vs generate)

`bundle` keeps the existing shape; **two new top-level keys** are added (additive, the
existing report assembler ignores them by default — non-breaking):

```
{
  target:           {...}             # same
  result:           TestGenerationResult.model_dump()  # same shape; see §2.1
  write:            WriteResult.model_dump()
  execution:        GenExecResult.model_dump()
  coverage_delta:   CoverageDelta.model_dump()
  preflight:        ...
  error:            ... | None

  # additive
  run_kind:         "external"        # NEW value alongside real/fake/dryrun/smoke (§3)
  producer_id:      string            # caller-declared, required, non-empty
  producer_meta:    dict              # caller-declared, free-form
}
```

### 2.1 `TestGenerationResult` for an external candidate

`TestGenerationResult` is reused **without schema change**; the orchestrator constructs it
deterministically from the request:

- `target_class`, `target_method`, `package`, `test_class_name`, `file_name` — derived from
  the resolved `Target` + the test_writer rename guard. **Caller cannot set them.**
- `test_source` — taken verbatim from the request body (the candidate).
- `model = producer_id` — so existing analytics/headlines (`group_by="model"`) keep working.
- `trusted = False` — **forced**, hard-coded; the schema already enforces `False` for the
  built-in path and we extend the same invariant here.
- `imports`, `scenarios`, `mocks`, `notes`, v2 grounding fields — all **default-empty**;
  callers may pass them in `producer_meta`, but they NEVER flow into `result.*` because
  external callers cannot self-certify grounding (anti-self-certification, parallel to
  invariant `is_anchoring` in `docs/48`).

The "platform-controlled identity, caller-supplied creativity" split that
`docs/07 P2` introduced for the generator path is *applied verbatim* to external submits.

## 3. `run_kind = "external"` (§5 expansion of docs/43)

`run_kind` today is `{real, fake, dryrun, smoke}` + historical `null`. We add `external`:

| `run_kind` | meaning |
|---|---|
| `real` | a real model produced the test inside this platform's generator |
| `fake` | the `FakeLLMClient` placeholder produced the test |
| `dryrun` | dry-run / cache hit / synthetic |
| `smoke` | smoke-test run |
| **`external`** | **the test came in via `submit_candidate`; no platform LLM call** |

The hardwired invariant `resolve_run_kind` enforces today — *"a fake client can NEVER be
'real'"* — becomes:

> A fake client can never be `real`. A `submit_candidate` entry can never be `real` or `fake` —
> it is always `external`. The caller cannot override `run_kind` on `submit_candidate`.

### 3.1 What `external` means for aggregates

`docs/43 §12` defaulted the headline view of `aggregate()` to `run_kind == "real"`. **No
change.** `external` lands in its **own bucket** (advisory), the same way `fake/dryrun/smoke`
do. The headline metric still describes "what our generator produced." A second view
(`aggregate(..., kind="external")`) becomes possible — useful for the "Claude vs Codex vs
human" comparison, but **not** the headline.

This keeps the existing fake/real separation intact and adds external as a peer signal.

## 4. Red-lines (the *whole point* of this endpoint)

These are non-negotiable; any S-slice that loosens them is rejected:

1. **`trusted` is `False`**, hard-coded. The `producer_id` is *who said this*, not *whether
   it's correct*. Models / humans / CLIs are all untrusted producers.
2. **`conclusion` stays `NEED_HUMAN_REVIEW`**, full stop. `submit_candidate` cannot accept.
3. **`auto_accept_blocked = True`** everywhere; the digest still emits it.
4. **No production-code / pom / existing-test edits.** The test_writer guards (write only
   under `src/test/java`, refuse to overwrite existing) apply unchanged.
5. **No oracle rewrite.** Compile-repair is *opt-in* in the generator path and stays opt-in
   here — and crucially, the same `repair_is_safe` guard applies. The default for
   `submit_candidate` is `repair_compile_failures=False` (a candidate that doesn't compile
   gets recorded as `COMPILE_FAILURE`, not silently repaired).
6. **`run_kind` is set by the endpoint, not by the caller.** Always `"external"`. There is
   no request parameter that lets a caller set `run_kind="real"`.
7. **No new dependency.** Reuses everything that exists today.
8. **No real-LLM call** is made by `submit_candidate`. The endpoint is *offline by
   construction* on the platform side (the *caller* may have used an LLM upstream; that's
   their problem).
9. **`producer_id` is manifest, not verification.** The platform does not authenticate
   "this really was Claude" or "this really was a human." It records what the caller said.
   This is consistent with how `run_kind` is producer-set (docs/43).

## 5. Job state machine (additive)

```
DONE -> TARGET_SELECT -> CONTEXT -> SUBMIT_EXECUTE -> COMPARE -> SUBMIT_DONE
        (any step may short-circuit to SUBMIT_FAILED)
```

Adds three new `JobStatus` values: `SUBMIT_EXECUTE`, `SUBMIT_DONE`, `SUBMIT_FAILED`. The
existing `GENERATE` / `GEN_EXECUTE` / `GEN_DONE` are unchanged. `TARGET_SELECT` and
`CONTEXT` are *reused* (the same transition rules apply on entry, but exit transitions are
extended: `CONTEXT -> {GENERATE, SUBMIT_EXECUTE, GEN_FAILED}`).

Rationale for distinct states: audit / `job.stages` should record *which producer path the
job took*. Reusing `GEN_DONE` for external submits would hide producer provenance in the
state machine, which contradicts the docs/43 ethos that *producer identity is
authoritative*.

A job that ran `/generate` cannot also run `/submit_candidate` — `SUBMIT_*` only transitions
in from `DONE`. (If the user wants both, that's two jobs.)

## 6. Validation rules (request-level, deterministic)

- `target_class` non-empty and resolvable in the repo (else 404/410 like generate).
- `target_method` optional; if set, must exist on the class (parallel to generate).
- `test_source` non-empty; size cap (e.g. 256 KB) to prevent DoS.
- `producer_id` non-empty; regex `^[A-Za-z0-9._@:+/-]{1,128}$` (alphanumeric +
  identifier-safe punctuation). Forbidden values: `"fake-1"` (reserved for FakeLLMClient),
  empty, whitespace-only. Rationale: a misleading `producer_id` is itself a form of
  hallucination; the input grammar resists it.
- `producer_meta`: dict, JSON-serializable, total serialized size ≤ 16 KB.
- `invariants`: optional list; each item validated by the existing `parse_invariants(...)`
  (docs/48). `is_anchoring` rules apply unchanged — model-declared invariants stay
  non-anchoring even when the producer is external.

## 7. What the report looks like (no new section needed)

The existing `assemble_generation_report` already emits `review_summary` with:
- `quality` (gate) + `oracle_strength_estimate` (docs/46)
- `mock_smells` (docs/51)
- `digest` (docs/52)

For an external candidate, all of those run **with no modification** — they read the same
`bundle` keys. The digest's headline will simply be informed by *that candidate's* smells /
oracle / quality, exactly as for a generated one.

Two cosmetic additions surface the producer:
- The report top-level gains `producer_id` (already in bundle).
- The MD report (`report_md`) gets one line: `_Producer_: <producer_id>` near the header.
  No verdict change; no flag change.

## 8. Where this lives (file plan)

```
app/api/submit_candidate.py            NEW — endpoint
app/pipeline/submit_pipeline.py        NEW — run_external_candidate(...) orchestrator
app/models/job.py                      EXTEND — JobStatus + transitions (additive)
app/llm/run_kind.py                    EXTEND — accept "external"; reject from caller
app/llm/schema.py                      EXTEND — TestGenerationResult.producer_id (str | None)
app/benchmark/runner.py                EXTEND — recognize run_kind=="external" in aggregates
docs/50_benchmark/53_SUBMIT_CANDIDATE_DESIGN.md  THIS FILE
```

Note: every "EXTEND" is additive — no existing behavior changes. The generator path keeps
its current types and transitions.

## 9. S-slices (each independently approvable)

### S1 — endpoint + pipeline + bundle (smallest landable) — **DONE 2026-06-15**
- `JobStatus.SUBMIT_EXECUTE / SUBMIT_DONE / SUBMIT_FAILED` + transitions
- `run_external_candidate(...)` reusing target / context / preflight / writer / executor /
  compare. **No LLM call**, no repair (default off).
- `run_kind="external"` forced; caller cannot override; `resolve_run_kind` extended.
- `POST /jobs/{id}/submit_candidate` endpoint; request/response schemas.
- Unit tests:
  - happy path: real test_source → bundle assembled, `assemble_generation_report` runs,
    `trusted=False`, `run_kind="external"`, `conclusion="NEED_HUMAN_REVIEW"`.
  - producer_id missing / invalid → 422.
  - producer_id == `"fake-1"` → 422 (cannot impersonate the fake client).
  - request-side `run_kind` field → ignored / rejected (defense in depth).
  - target unresolvable → `SUBMIT_FAILED` with reason.
  - test_source that fails preflight → `SUBMIT_DONE` with `PREFLIGHT_REJECT` recorded
    (same path as generate; the gate doesn't change).
  - existing generated path **unchanged** (regression: `/generate` still works; aggregates
    still treat `external` as non-real).

### S2 — provenance first-class + charter invariant proven — **DONE 2026-06-15**
**Audit finding (2026-06-15):** the analytics layer needed **no new code** — `aggregate()`
(`benchmark/models.py`) and `_filter_kind()` (`ledger/analytics.py`) are generic
`run_kind == <kind>` filters, so `external` is *already* a peer of `real/fake/dryrun/smoke`:
`run_kind="real"` excludes it from the headline; `run_kind="external"` gives the per-producer
view. S2 therefore reduced to **(a)** making provenance first-class and **(b)** proving the
charter invariant by test.
- `assemble_generation_report` now surfaces `producer_id` (from `result`, falling back to the
  bundle) and `run_kind` as top-level provenance — advisory, never a warrant (`trusted` stays
  `False`). On a generator run `producer_id` is `None` and `run_kind` is `real/...`.
- API cleanup: whitespace-only `target_method` normalizes to `None`.
- Unit tests (`tests/test_submit_candidate_s2.py`, 8): external excluded from the real
  headline (`aggregate` + `aggregate_badcases`); external-only view; all-kinds view; "external
  cannot masquerade as real" (the parallel to "fake can never be real"); report surfaces
  producer/run_kind; generator-path back-compat; bundle-fallback for producer_id.
- **Deferred:** the benchmark **report_md** per-case producer line is moot until external
  candidates flow through the *benchmark* runner (they don't yet — submit is per-job via the
  API). Re-open if/when a benchmark ingests external candidates.

### S3 — invariants + gated mutation
- `submit_candidate` accepts `invariants` (docs/48 InvariantDescriptor) → flows into bundle
  → invariant_review surfaces in the digest.
- Mutation stays gated off (no change); when enabled, `_attach_invariant_mutations` works on
  external candidates because it's purely pipeline-local — verified by a unit test.
- Unit tests:
  - manifest-supplied invariant on an external candidate: anchoring rules unchanged
    (manifest is anchoring; model-declared in producer_meta is non-anchoring).
  - mutation gated path off: bundle still complete, no PIT call.

### Deferred (not in any S-slice; explicit approval required)
- A persistent endpoint for "compare this Claude candidate vs this Codex candidate vs the
  generator" (a *batch* submit). Solvable inline by the caller running three submits.
- Authenticating `producer_id` (signed manifest, etc.). Out of scope; trust model stays
  "caller's word, recorded."
- Browser UI / CLI client. Out of scope.

## 10. Acceptance (for owner sign-off on the design)

- `POST /jobs/{id}/submit_candidate` exists with the request schema in §1.
- The returned bundle has `run_kind == "external"`, `producer_id == <caller's value>`,
  `result.trusted == False`, `result.model == producer_id`.
- `GET /jobs/{id}/generation` returns the existing report shape; the digest is built
  from the same signals; `conclusion == "NEED_HUMAN_REVIEW"`, `auto_accept_blocked == True`.
- No test of `/generate` regresses. No analytic of `real-only` headlines changes (external
  is not counted toward `real`).
- Charter test in code: a `run_kind="external"` row can never be merged into the `real`
  headline view (parallel to the existing fake-can't-be-real assertion).

## 11. Open questions for the owner

1. **State name preference**: `SUBMIT_EXECUTE` vs `EXTERNAL_EXECUTE`? The former is shorter
   and matches the endpoint name; the latter is more explicit about *external* provenance.
   Recommendation: `SUBMIT_EXECUTE`.
2. **Compile-repair default**: keep off (recommended; preserves the "we record facts" stance
   for external candidates) or follow the generate default? Recommendation: **off by
   default**; expose an opt-in flag mirroring `/generate`.
3. **Multi-test source**: today, the generator yields one test class per call. Should
   `submit_candidate` accept multiple test files at once? Recommendation: **no, S-slice-1
   handles one**; multi-file is an S4 if ever needed.

---

> The endpoint adds no judging logic. It opens the judge to producers other than the
> built-in generator, holds the verdict invariants harder than ever (trusted=False forced;
> run_kind=external forced), and lets the existing digest do its job. The product stays the
> **judgment** — now demonstrably *producer-agnostic*, not just *generator-coupled*.
