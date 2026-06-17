# Context v3 → v3.2.3 — Evolution Digest (consolidated)

> **Consolidates** the nine per-run review logs `25,26,27,28,29,30,31,35,37`
> (2026-06-07) into one digest. Originals removed; full text recoverable via git
> history. **Status: generation-side, maintenance mode** (docs/40 §5) — the durable
> output is the *lessons*, not the per-run detail. All runs: `deepseek-v4-pro`,
> repair OFF, coverage skipped, **no oracle auto-fix, every conclusion `NEED_HUMAN_REVIEW`.**

## 0. What this arc was
An iterative **prompt/context-hardening** effort on `app/generate/prompt_builder.py`:
add deterministic SYSTEM_PROMPT rules so the built-in generator avoids *mechanical*
failures (overload ambiguity, reflection, ungrounded oracles, `@Nested` mis-reporting)
**at generation time**, instead of repairing them later. No parser/pipeline/oracle change
in the whole arc. It directly fed the deterministic **preflight gate** (see
`PREFLIGHT_EVOLUTION_DIGEST.md`).

## 1. The versions (what each added)
| Ver | Doc | Change (prompt rules unless noted) |
|---|---|---|
| v3 | 25,26 | method-contract / exception-oracle grounding; `body_throws` is *supporting* evidence only (exact exception needs declared/`@throws`/neighbor evidence) — fix `35c8649` |
| v3.1 | 27,28 | rule 7 [overloads/generics] (cast null, typed varargs arrays, no wildcard→concrete); rule 8 [API grounding] (public APIs only, no reflection/private ctor); rule 9 [oracle grounding] (don't infer state from constants/Javadoc; doc≠source → skip) |
| v3.2 | 29,30 | render field initializers + bounded ctor bodies (state evidence); strengthen primitive/boxed varargs rule; "method not in rendered list → skip"; conditional/catch throw ≠ normal-path oracle; don't guess exact string/entity maps; **forbid `@Nested`** (flat `@Test` only) |
| v3.2.1 | 31 | varargs positive paths must use a *named typed-array variable* |
| v3.2.2 | 35 | same-arity reference overloads differing by type → cast `null` to evidenced type or skip |
| v3.2.3 | 37 | same-arity primitive/boxed family → never mix boxed+primitive args in one call |

## 2. Benchmark trend (10-case `manifest.v1`, 1 sample/case)
| Metric | v3 (26) | v3.1 (28) | v3.2.3 (37) |
|---|---:|---:|---:|
| compile pass rate | 60% | **80%** | **50%** |
| generated-test pass rate | 20% | 30% | 20% |
| strong candidates | 2 | 3 | 1 |
| top failure types | TEST4 COMP3 PIPE1 | TEST4 COMP2 NOTESTS1 | COMP5 TEST3 |
| need_human_review | 100% | 100% | 100% |

(3-case bodyfix baseline `docs/25`: compile 100%, pass 67%. 4-case v3.2 `docs/30`:
compile 75%, pass 50% — `BooleanUtils` still failed compile.)

## 3. The five durable lessons (why this arc was stopped)
1. **A single 10-case run is too noisy to rank prompt versions** (n=10, 1 sample/case,
   model-nondeterministic — cases flip PASS↔FAIL between runs, e.g. `CommandLine`,
   `StringEscapeUtils`). Use the benchmark for **failure-class discovery**, not as a
   quality score. v3.2.3 "regressing" to 50% compile vs v3.1's 80% is noise, not proof
   the later prompts are worse.
2. **Prompt compliance is unreliable for compiler-enforced overload edge cases.** The
   decisive evidence: `BooleanUtils` emitted the exact `toBoolean(null)` form v3.2.2
   forbids — complied once (docs/35), regressed next run (docs/37). Each prompt rule
   fixed one overload sub-shape and surfaced the next (individual values → named array →
   bare null → mixed boxed/primitive). → motivates the **deterministic preflight gate**.
3. **Prompt-rule bloat hits diminishing/negative returns.** Compile failures went
   3→2→**5** as the rule count grew; the 5 were *diverse* buckets (overload, missing
   static import, instance-arg-type, generics wildcard) that no single rule addresses.
4. **Doc ≠ implementation is a real, must-surface signal, never auto-fixed.**
   `Option.getValues()` returns `null` while Javadoc says empty array; the model followed
   docs and failed. The platform must surface this to the reviewer, not rewrite the oracle.
5. **What prompt hardening *can* do:** reliably remove some mechanical failures
   (`NumberUtils` overload, `WordUtils` reflection, `CSVFormat`), and make the model
   honestly *skip* ungrounded behavior (`omitted_uncertain_cases`). Real, but bounded.

## 4. Red-lines held throughout
No oracle auto-fix; `TEST_FAILURE` / doc-conflict stayed `NEEDS_REVISION`/`REJECT_CANDIDATE`;
`conclusion` always `NEED_HUMAN_REVIEW`; bounded context preserved (fixed rule text, not repo
dumps — prompt stayed <6000 chars); no repair loop; no coverage restoration.

## 5. Where it led
- The deterministic **preflight gate** (`app/quality/generated_test_preflight.py`,
  docs/32–36 → `PREFLIGHT_EVOLUTION_DIGEST.md`) became the robust backstop for the
  overload class that prompt rules couldn't reliably prevent.
- Generation-side prompt tuning entered **maintenance mode** (docs/40 §5): only touched
  for an oracle-safety/red-line reason, not to chase compile/pass rate.
- Evidence dirs (read-only): `var/benchmark/v3-pro-10case`, `v3_1-pro-10case`,
  `v3_2-pro-4case`, `v3_2_1-pro-booleanutils-retry1`, `v3_2_2-pro-booleanutils`,
  `v3_2_3-pro-10case`.
