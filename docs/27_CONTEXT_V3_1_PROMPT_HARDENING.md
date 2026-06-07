# Context v3.1 — Prompt/Context Hardening

> Date: 2026-06-07. Scope: **prompt hardening only** (additive SYSTEM_PROMPT
> rules). No new model run here, no parser/context-data change, no Phase 3
> repair, no oracle auto-fix. Upstream evidence: `docs/26` (v3 pro 10-case).

---

## 0. Why

The Context v3 10-case pro run (`docs/26`, `var/benchmark/v3-pro-10case`) confirmed
v3 fixed the exception-contract failures but exposed three *new, deterministic*
failure shapes. v3.1 hardens the generation rules to prevent them **at generation
time**, instead of repairing them later. This is exactly the narrow step `docs/26`
§6 recommended ("do not move directly into broad Phase 3 repair").

The data is already in the prompt (overloaded signatures, constructors, neighbor
tests are rendered by `_methods_block`/`_ctors_block`/`_neighbor_block`), so v3.1
is **pure prompt hardening** — no parser or context-data change.

---

## 1. Rules added (SYSTEM_PROMPT, `app/generate/prompt_builder.py`)

| # | Rule (block) | 10-case failure it targets (`docs/26` §3) |
|---|---|---|
| 7 | **[Overloads and generics]** — never pass bare `null` or an untyped array to an overloaded method; cast each null to the intended type (`(String) null`); build varargs as an explicitly typed array (`new boolean[]{true}`); don't assign a wildcard `List<?>` to a concrete `List<Option>` | `Options` (wildcard mismatch), `NumberUtils.toDouble(null,…)` (ambiguous overload), `BooleanUtils` (`and/or/xor/oneHot` varargs, `toBoolean(null)`) — the 3 `COMPILE_FAILURE` |
| 8 | **[API grounding]** — test only public, observable APIs; never use reflection (`setAccessible`/`getDeclared*`) or call a private constructor, even if a neighbor test does, unless the target itself is that constructor's behavior | `WordUtils` reflection/private-constructor test → quality gate `FAIL` |
| 9 | **[Oracle grounding]** — do not infer post-construction field/state from constants or Javadoc alone; if state isn't shown by source / neighbor test / constructor body, SKIP. If Javadoc conflicts with the method's return type/source (doc says empty array, source returns `null`), treat as uncertain → SKIP and note, do not assert the documented value | `Option.getValues()` returned `null` while Javadoc said empty array (doc≠impl) |

These extend the existing v2 buckets (1–5) and v3 bucket (6, exception contract).
Tests pin each new rule to its bucket: `tests/test_prompt_builder.py`
(`test_v3_1_*`).

---

## 2. Explicitly deferred (not v3.1)

- **Deep constructor/state grounding** (compact constructor/state summaries or
  selected constructor bodies) → Context v4 (`docs/25` §6.1, `docs/26` §4.2). v3.1
  only tells the model to *skip* ungrounded state, not to supply more of it.
- **Invalid-JSON bounded retry** (`Validate` `PIPELINE_FAILED`) → a provider-layer
  concern, separate from prompt hardening and from oracle repair (`docs/26` §4.3).
- **Compile-only Phase 3 repair** → reconsidered only *after* v3.1, since
  preventing overload ambiguity at generation time is the stronger move
  (`docs/26` §6).

---

## 3. Red-lines (unchanged)

- No oracle auto-fix: `TEST_FAILURE` and doc≠impl conflicts stay
  `NEEDS_REVISION`/`REJECT_CANDIDATE`; `conclusion` stays `NEED_HUMAN_REVIEW`
  (`docs/07` A5, `docs/22`).
- Bounded context preserved (`docs/07` P4): v3.1 adds fixed *rule* text, not repo
  content.

---

## 4. Validation

- **Offline (done, zero model cost):** full suite **168 passed, 4 skipped**.
  `tests/test_prompt_builder.py` asserts the three rules render in SYSTEM_PROMPT;
  `tests/test_generation.py::test_prompt_does_not_dump_whole_repo` bound raised to
  6000 (fixed-rule growth; a repo dump would be an order of magnitude larger).
- **Next (needs explicit confirmation — spends model budget):** re-run
  `benchmarks/manifest.v1.json` with v3.1 + `deepseek-v4-pro` →
  `var/benchmark/v3_1-pro-10case`, repair disabled, coverage skipped.

  Acceptance (vs `v3-pro-10case`, `docs/26`):
  - the 3 `COMPILE_FAILURE` (Options/NumberUtils/BooleanUtils) should drop or move to PASS;
  - `WordUtils` should stop producing a reflection/private-ctor test;
  - strong candidates (`CommandLine`, `StringEscapeUtils`) must not regress;
  - genuine oracle/doc-conflict cases (`Option`, `CSVRecord`, `CSVFormat`) should
    correctly remain `NEEDS_REVISION` (skipped, not wrongly asserted) — **not**
    auto-fixed.

> Success is not "all pass". Success is fewer mechanical compile/reflection
> failures and more cases that either pass on grounded oracles or honestly skip
> ungrounded ones — while the platform still never auto-accepts.
