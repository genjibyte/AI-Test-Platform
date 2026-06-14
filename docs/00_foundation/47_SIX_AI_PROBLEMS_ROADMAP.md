# 47 — Six AI problems roadmap (owner-articulated 2026-06-14)

> **Status: NOT started. Design-mapping only.** This file records the owner's six target
> problems and maps each onto what the repo already has, what is genuinely new, and which side
> of the thesis it serves. **Nothing here is approved for implementation** — each item needs an
> explicit go + its own design pass first. All future signals stay **advisory**: `conclusion`
> remains `NEED_HUMAN_REVIEW`, `trusted=False`, no auto-accept, no oracle auto-fix.

## Thesis lens (read first)
The product is the **judge** — "can I tell whether an AI test has engineering value?" Generation
is **one producer** (charter, `40_CORE_THESIS_REPOSITIONING.md`). So split the six by which side
they improve, and keep judge-side primary:

- **Judge / precipitation side (on the core thesis):** #1 (as *verification* of invariants),
  #3 assertion quality, #6 badcase memory.
- **Generation-producer side (valuable, but "one producer" — secondary):** #2 context retrieval,
  #4 mock library, #5 multi-round repair. Better producers feed the judge better candidates, but
  they must never become the product, and never relax a verdict.

## The six, mapped to current state

### 1. Business-contract understanding
*Goal:* know the method's business rules (order/coupon/permission/payment), test state
transitions, boundaries, exception paths, side-effects — not just call signatures.
- **Foundation now:** `app/benchmark/business_tags.py` + `docs/45` carry
  `business_domain/pattern/expected_invariant/risk_level` as **declared, untrusted intent**.
- **New:** actually *extracting/verifying* contracts (not just tagging), and turning
  "boundary/exception/side-effect" into checkable expectations.
- **Boundary:** declared-intent stays untrusted; *verifying* an invariant is judge-side and on-
  thesis; *feeding* it to a generator is producer-side. Never let a declared invariant become a
  pass.
- **Design drafted (2026-06-14, not approved for code):** `docs/50_benchmark/48` — verify the
  *test pins the declared invariant* (coverage + assertion + line-scoped mutation), advisory;
  model-declared invariants never self-certify.

### 2. Context retrieval
*Goal:* find the most relevant code, DTO, Enum, existing tests, mock examples, config — don't
dump the whole repo at the model.
- **Foundation now:** `app/context/` (`context_collector`, `class_index`, `java_parser`,
  `maven_deps`) + `app/generate/prompt_builder.py` already assemble scoped context.
- **New:** relevance *ranking* / retrieval (RAG-style) over that index; example/mock selection.
- **Boundary:** producer-side. Improves candidate quality; changes no verdict.

### 3. Assertion quality  ← most built; natural next step
*Goal:* judge assertion *strength*, not just "does it run". `assertNotNull` /
`assertDoesNotThrow` / empty method calls are weak. Mutation, assertion classification, and
**survived-mutant explanation** belong in the report.
- **Foundation now:** `app/quality/test_quality_gate.py` (weak-assertion detection),
  `app/quality/oracle_strength.py` (structural estimate, `docs/46`), and the **mutation**
  subsystem (`app/mutation/`, validated 2026-06-14, `docs/46` §15–16).
- **New:** assertion *taxonomy*; and **survived-mutant classification** — `docs/46` §16 already
  showed survivors come in kinds (real coverage gap vs *equivalent mutant* vs trivial); the
  report must explain, not just count.
- **Boundary:** judge-side, core thesis. Stays advisory.

### 4. Mock & object construction
*Goal:* a mock-pattern library — how to test a Controller, mock a Service, handle a Repository,
pin time/randomness; avoid mocking the wrong method / wrong return type / real external calls.
- **Foundation now:** none (no mock module).
- **New:** a pattern library; detection of mock smells (real external call, wrong-type stub).
- **Boundary:** mostly producer-side (helps generation). A *detector* for "calls a real external
  dependency" could be judge-side (a red flag), and is the on-thesis slice of this item.

### 5. Multi-round repair
*Goal:* repair by error type — compile-fail, run-fail, assertion-fail, no-coverage-gain, low-
mutation, flaky, mock-error each get a different strategy.
- **Foundation now:** `app/repair/compile_repair.py` + `app/quality/generated_test_preflight.py`
  exist (oracle-safe compile-repair, **gated off**; `docs/38`, `docs/39`).
- **New:** generalize to an error-type → strategy router for the other failure classes.
- **Boundary:** producer-side, and the **highest-risk** for the thesis. Hard red-line:
  repair may **never** rewrite expected→actual, weaken/delete assertions, or touch
  production/pom/existing tests. Verdict stays `NEED_HUMAN_REVIEW`.

### 6. Badcase memory / RAG knowledge base
*Goal:* every failure precipitates structured experience (error type, root cause, fix, scope);
retrieve similar history before generating.
- **Foundation now:** `app/ledger/` (P1/P2 badcase ledger: `models`, `ingest`, `store`,
  `analytics`) already structures judged records.
- **New:** a retrieval layer over the ledger (similarity search), and richer root-cause/fix
  schema feeding both the judge (priors) and the producer (hints).
- **Boundary:** the ledger/precipitation is judge-side and on-thesis; using it to *hint
  generation* is producer-side. Historical `bench.db` stays read-only — no backfill.

## Suggested sequencing (owner decides; nothing started)
1. **#3 survived-mutant classification** — smallest, builds directly on the 2026-06-14 runs;
   pure judge-side; turns today's finding into a report feature.
2. **#6 retrieval over the existing ledger** — foundation already exists; judge-side priors.
3. **#1 invariant *verification*** (vs the declared tags) — judge-side.
4. **#2 / #4 / #5** producer-side improvements — valuable, but secondary per the thesis; #5
   only behind the existing oracle-safety red-lines.

## Red-lines (unchanged, apply to all six)
Advisory only; no auto-accept; no oracle auto-fix; no production/pom/existing-test edits; mutation
stays gated/opt-in; no new dependency without stop-and-ask; historical data read-only.
