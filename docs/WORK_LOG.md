# Work Log — context snapshot + project audit

> Refreshed 2026-06-13, immediately before a planned `/compact`. **Single** context file:
> read this + `CLAUDE.md` to resume without re-deriving context. The value-judgment signal
> layer is built, merged, and audited. Project = **AI-generated unit-test candidate
> judge/audit platform** — *"judge, don't generate."* Every new signal is **advisory**;
> nothing auto-accepts.

## 0. Project audit (2026-06-13; re-verified 2026-06-14) — evidence-based, all PASS

- **State:** branch `main` @ HEAD, **19 commits ahead of `origin/main`** (push is human-only),
  working tree clean, only `main` exists. Repo healthy. (Re-verified 2026-06-14: audit +
  real-repo mutation run + invariant-verification #1 complete + survived-mutant classify #3 S1.)
- **Tests:** full suite **312 passed / 4 skipped** (316 `<testcase>` nodes, 0 fail / 0 error;
  the 4 skips are the `TESTAGENT_E2E`-gated e2e tests). `EXIT=0`. (… → 304 #1 complete → 312
  #3 survived-mutant classify S1.)
- **Core invariants INTACT:** `trusted` is hardwired `False` (`app/llm/schema.py`,
  deterministic — model can't set it); `accept_rate=None` (`aggregate`); `auto_accept_blocked=True`;
  `conclusion` stays `NEED_HUMAN_REVIEW`. The four signals below are **read-only/advisory**
  — **none** feed `recommend_with_reasons` or `conclusion` (verified by grep:
  `recommend_with_reasons` takes only `quality_status/gen_outcome/production_code_touched/
  repair_applied/model_risk`).
- **Scope/thesis:** on-thesis — all additions are judging/value signals; no drift into
  generation/UI/RAG. Mutation/PIT is **gated off + opt-in** (no silent dependency).
- **Docs:** `CLAUDE.md` fact-corrected this session; `docs/43/44/45/46` accurate. Consistent.
- **No outstanding risks.**

## 1. What's built — the value-judgment signal layer (all on `main`)

1. **`run_kind`** (`real`/`fake`/`dryrun`/`smoke`) — S1 minimal slice + S2 headline-default
   to `real` (`aggregate()` + ledger analytics; fake/dryrun/smoke + historical unknown
   excluded; back-compat). Invariant "fake can never be real" (regression-tested). `docs/43`.
2. **Business-invariant tags** (`business_domain`/`business_pattern`/`expected_invariant`/
   `risk_level`) — S1 schema+carry, S2 descriptive group-by (composes with `run_kind==real`),
   S3 advisory human-review rubric in `review_summary`. `app/benchmark/business_tags.py`,
   `docs/45`. **Declared intent, not verified value**; case-level authoritative, model-declared
   untrusted.
3. **Oracle-strength — STRUCTURAL** — `estimate_oracle_strength()` rolls up the quality
   gate's facts (`no_assertions`/`only_weak`/`tautological`/`weak_assertion_heavy`) into an
   advisory `none/weak/mixed/structural_ok/unknown` surfaced in `review_summary`
   (`oracle_strength_estimate`); S2 carry + group-by. `app/quality/oracle_strength.py`,
   `docs/46`. `semantic_strength` stays `"human_review"`.
4. **Oracle-strength — SEMANTIC = mutation (the real signal)** — **dormant gated** PIT
   subsystem `app/mutation/`: `parse_pit_report`, `build_pit_command`, `build_pit_pom`
   (JUnit5-aware **sidecar** pom builder — injects `pitest-maven` + `pitest-junit5-plugin`,
   **no original-pom edit**), `run_pit` (uses the sidecar; JUnit4 fallback), and the gated
   `_maybe_mutation_score` benchmark wire-in. `mutation_enabled=False` default → PIT is
   **never** fetched/run unless explicitly enabled. `docs/46` S3 + §14.
   **Validated by a real PIT run** on a throwaway `samples/calc` copy: PIT reported 5/4/80%,
   and `build_pit_pom`'s generated sidecar reproduced it — parser confirmed against real
   `mutations.xml` (`mutation_score 0.8 == PIT 80%`).

## 2. Git state

`main` @ `c800a08` == `origin/main` (0 unpushed), clean tree, only `main` branch. Recent
merges (newest first): `c800a08` run_pit sidecar → `e299553` JUnit5-aware builder →
`5c4365f` dormant mutation core → `ca2edf6` oracle S2 → `e3c597d` oracle S1 →
`d72f271` business-tags S3 … (run_kind S2 + business-tags + oracle + mutation arc).

## 3. Verify commands (venv only)

Use the venv python — bare `python` is the Windows Store stub (exit 49, no output):
`& "E:\AI-Test-Platform\.venv\Scripts\python.exe" …`
- `… -m pytest -p no:warnings -q` → **267 passed, 4 skipped** (271 `<testcase>`, EXIT=0).
- `… scripts/audit_bench.py` → reproduces `docs/42` §A (historical heuristic: real n=67,
  compile 61% / pass 25% / green-FAIL 0/17; 0 authoritative run_kind).
- Toolchain present: Maven **3.9.9**, JDK **17**, mvn.cmd at
  `C:\Users\lenovo\AppData\Local\Programs\Maven\apache-maven-3.9.9\bin\mvn.cmd`.

## 4. Next steps (all need explicit approval / manual trigger)

- **DONE 2026-06-14 — gated mutation run through the merged path** (`8168263`, docs/46 §15):
  real PIT run on throwaway `samples/calc` copies via merged `run_pit`/sidecar →
  real test **0.8** (verified line-by-line vs PIT raw xml; survivor = `max` `>`→`>=`),
  **negative control** green-but-empty zero-assertion test → **0.0** (5/5 SURVIVED) =
  the fake-pass guard proven. Found+fixed a Windows defect (`run_pit` couldn't launch bare
  `mvn`=`mvn.cmd` → resolved via `shutil.which`). `samples/calc` & live benchmark untouched;
  `mutation_enabled` back to `False`.
- **DONE 2026-06-14 — first real-repo run** (docs/46 §16): commons-cli `OptionValidator` +
  its real Apache JUnit5 test → **0.8947** (19/17/1/1, grep-verified); survivors classified =
  1 coverage gap (`validate(null)` untested) + 1 *equivalent mutant* (`>1` vs `>=1`). Proves
  the path scales to a real multi-class Maven repo, and that **survivors need explanation, not
  just counting**.
- **Optional follow-ups:** classify/explain survived mutants in the report; surface
  `mutation_score` (bucketed) in report/group-by. Both advisory; never auto-accept.
- **Roadmap (owner, 2026-06-14) — six AI problems:** see
  `docs/00_foundation/47_SIX_AI_PROBLEMS_ROADMAP.md` (judge-side #1/#3/#6 on-thesis;
  producer-side #2/#4/#5 secondary). Each remaining item needs explicit approval + a design pass.
- **DONE 2026-06-14 — #1 design + S1 + S2 + S3** (design `docs/48`): "invariant verification"
  reframed as *does the candidate TEST pin the DECLARED invariant?* (coverage + assertion +
  line-scoped mutation), never "is the code correct".
  - **S1** (`6f69a3f`): `InvariantDescriptor` + carry case→result→ledger + advisory
    `review_summary["invariant_review"]`; anti-self-certification (model-declared = non-anchoring).
  - **S2** (`3ce3eb0`): `estimate_invariant_strength` → `invariant_strength`
    {unaddressed/addressed_unasserted/asserted_unpinned/pinned/unknown}; `asserted` reuses
    `oracle_strength`; honest "unknown" when coverage off. Advisory; verdict never changes.
  - **S3** (`2179a39`): `parse_pit_report(include_mutations=)` + `parse_line_spec` +
    `scoped_mutation_score` → `pinned` ONLY when all invariant-scoped mutants are killed (else
    `asserted_unpinned` + `scoped_mutants_survive` = gap OR equivalent, never condemned).
    **Validated on commons-cli `OptionValidator.validate()`** (gated PIT): scoped 0.8 (8/10) →
    honest `asserted_unpinned`. Non-anchoring never pinned even with a perfect score.
  - **Live wire-in** (`_maybe_mutation` + `_attach_invariant_mutations` in runner): gated PIT runs
    once, rows re-scope the invariant view so the LIVE benchmark reaches `pinned` automatically.
    Mutation evidence implies reachability, so `pinned` works even with coverage off. Unit-tested;
    a full end-to-end live run with *real generation* needs API/cost (not run). **#1 complete.**
- **IN PROGRESS — #3 survived-mutant classification** (design `docs/49`): explain WHY a mutant
  survived (never assert equivalence — undecidable; never condemn a test).
  - **S1 done** (`app/mutation/survivors.py` `classify_survivors`): buckets non-killed mutants →
    `not_covered` / `survived_weak_oracle` / `survived_maybe_equivalent` / `survived_unclassified`
    + mutator explanation + `equivalence_likelihood`; matches the §16 `validate()` finding. Advisory.
  - **S2 (pending, needs approval):** surface classified survivors in the invariant view
    (`scoped_mutants_survive`) + a "Survived mutants" section in `report_md.py`.
- **Deferred — do NOT start without explicit approval:** #3 S2; other roadmap items (#2 context
  retrieval, #4 mock library, #5 multi-round repair, #6 ledger RAG), P3 / `submit_candidate`,
  Defects4J, multi-model experiments.

## 5. Forbidden / red-lines (unchanged)

No auto-accept (`conclusion` stays `NEED_HUMAN_REVIEW`, `trusted=False`); no oracle rewrite
(never weaken/delete assertions). No production/pom/existing-test edits as part of
generation. **Never read, print, summarize, or commit `.env`.** No real model/API calls
without explicit confirmation (state command + cost first). **Push is human-only.** Never
backfill/mutate historical `var/benchmark/*/bench.db`. No new dependencies without
stop-and-ask (PIT is gated/opt-in, fetched only on an explicit mutation run). No
judging/quality-gate/oracle logic change. No S-slice without owner approval.

## 6. Key conclusions to retain

- The four advisory signals never auto-accept; **semantic value stays human review** (+ real
  mutation evidence when explicitly enabled).
- **Mutation gated off** by default. **JUnit5 needs `pitest-junit5-plugin`** → supplied via
  `build_pit_pom`'s sidecar (`docs/46` §14); the command-line "no pom edit" form only works
  for JUnit4.
- **`run_kind` contamination history** (`docs/44`): raw n=80 mixed 13 fake/dryrun → real
  n=67; the "43% green-but-worthless" claim was **retracted**; headline metrics = authoritative
  `real` only.
- **Toolchain:** venv python only; E: drive had a one-off delayed-write incident this session
  (recovered) — if git acts up, verify *durable* writes (WriteThrough+flush) before retrying.
- **Read-first for the next agent:** `CLAUDE.md`; `docs/00_foundation/{00 charter, 40 thesis,
  42 audit, 44 decisions}`; `docs/50_benchmark/{43 run_kind, 45 business-tags, 46 oracle/mutation}`;
  `docs/knowledge/README.md`.
