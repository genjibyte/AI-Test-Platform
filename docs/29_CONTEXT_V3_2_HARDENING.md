# Context v3.2 — Prompt/Context Hardening (state + 5 rules)

> Date: 2026-06-07. Scope: **prompt/context hardening only**. No repair loop
> (explicit user constraint "不做修复闭环"), no model run here, no parser change,
> no oracle auto-fix. Driven by the v3.1 pro 10-case review `docs/28`.

---

## 0. Why

The v3.1 pro 10-case run (`docs/28`, `var/benchmark/v3_1-pro-10case`) moved compile
60%→80% and strong candidates 2→3, but exposed concrete residuals and two
regressions. `docs/28` §7 specifies v3.2 as a narrow prompt/context pass (not Phase
3 repair). This change implements that spec plus the constructor/state grounding
from `docs/26` §6.2 — all of it prompt/context, all additive and deterministic.

---

## 1. What changed (`app/generate/prompt_builder.py`)

| # | Change | Kind | Targets (`docs/28`) |
|---|---|---|---|
| 1 | Render field **initializers** + **bounded constructor bodies** (`sets: …`, ≤240 chars); headers say "post-construction state evidence" | context data | `Option` argCount / `Options`,`CommandLine` state (§6.2, §6.3) |
| 2 | **[Overloads and generics]**: for methods with primitive **and** boxed overloads, never pass individual values or bare null — pass one typed array (`new boolean[]{…}`/`new Boolean[]{…}`) and cast null to the exact type (`(Boolean) null`, `(String) null`, `(Integer) null`) | prompt rule | `BooleanUtils` `COMPILE_FAILURE` (§6.7) |
| 3 | **[API grounding]**: before calling any method, confirm it appears in the rendered method list; if not listed, it doesn't exist in this version — skip | prompt rule | `CSVRecord.putInMap` not-found (§6.4) |
| 4 | **[Oracle grounding]**: a body-contains-throw fact is supporting evidence **and may be conditional** (catch/if) — not proof the normal path throws | prompt rule | `Option.testCloneThrows` (§6.1) |
| 5 | **[Oracle grounding]**: do not assert exact string-transformation outputs (escaping, entity maps like `&gt;`, encoding, formatting) unless the exact value is in source/neighbor — else skip | prompt rule | `StringEscapeUtils` (§6.5) |
| 6 | **[Test strategy]**: use flat `@Test` only; do **not** use `@Nested` (the build reads the top-level surefire report) | prompt rule | `Validate` false `NO_TESTS` (§6.6) |

The state data (#1) was already parsed (`JavaField.raw`, `JavaConstructor.source`) —
v3.2 just renders it, bounded. Rules #2–#6 are additive SYSTEM_PROMPT text. No
parser/model/runner change. Tests pin each to its bucket
(`tests/test_prompt_builder.py::test_v3_2_*`).

> `@Nested` route choice: `docs/28` §6.6 offers prompt-forbid vs harness-aggregate.
> v3.2 takes the **prompt-forbid** route because it is smaller (§7.2). The harness
> route (aggregate `GeneratedTest$*` surefire reports) stays open if nested tests
> are later wanted.

---

## 2. Explicitly deferred (still not v3.2)

- **Per-method return-body grounding** — `Option.getValues()` returns `null` while
  Javadoc says empty array; needs the *method* body (whole-class targets don't
  render it). Context v4. Until then rule 9's doc≠source skip applies.
- **Invalid-JSON bounded retry** — provider-layer, not prompt/context.
- **Harness `@Nested` aggregation** — the more-correct alternative to the prompt
  forbid; deferred.
- **Compile-only Phase 3 repair** — out of scope by explicit user constraint.

---

## 3. Red-lines (unchanged)

- No oracle auto-fix; `conclusion` stays `NEED_HUMAN_REVIEW` (`docs/07` A5, `docs/22`).
- Bounded context (`docs/07` P4): initializers capped 80, constructor bodies 240;
  fixed rule text only — a repo dump would be orders of magnitude larger.
- No repair loop this round.

---

## 4. Validation

- **Offline (done, zero model cost):** full suite **174 passed, 4 skipped**.
- **Next (needs explicit confirmation — spends model budget):** `docs/28` §7
  recommends a **targeted 4-case validation first** —
  `BooleanUtils`, `Validate`, `CSVRecord`, and one regression sentinel
  (`StringEscapeUtils` or `CommandLine`) — before re-running the full 10-case.

  Acceptance:
  - `BooleanUtils` compiles (typed varargs / cast null); `Validate` reports real
    test counts (no `@Nested`); `CSVRecord` does not call an unlisted method;
    the sentinel does not regress to a guessed oracle;
  - genuine oracle/doc-conflict cases still surface as `NEEDS_REVISION` — never
    auto-fixed.

> Success is not "all pass". Success is fewer mechanical compile/measurement
> failures and more honest skips on ungrounded behavior — while the platform
> still never auto-accepts.
