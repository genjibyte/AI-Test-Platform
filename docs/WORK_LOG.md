# Work Log — context snapshot + project audit

> Refreshed 2026-06-13, immediately before a planned `/compact`. **Single** context file:
> read this + `CLAUDE.md` to resume without re-deriving context. The value-judgment signal
> layer is built, merged, and audited. Project = **AI-generated unit-test candidate
> judge/audit platform** — *"judge, don't generate."* Every new signal is **advisory**;
> nothing auto-accepts.

## 0. Project audit (2026-06-13; re-verified 2026-06-14) — evidence-based, all PASS

- **State:** branch `main` @ HEAD, **2 commits ahead of `origin/main`** (push is human-only),
  working tree clean, only `main` exists. Repo healthy. (Re-verified 2026-06-14: audit + real-repo
  mutation run + #1 invariant-verification + #3 survivor classify + #6 retrieval + #4 mock-smell S1.)
- **Tests:** full suite **389 passed / 4 skipped** (393 `<testcase>` nodes, 0 fail / 0 error;
  the 4 skips are the `TESTAGENT_E2E`-gated e2e tests). `EXIT=0`. (… → 381 docs/53 S1 submit_candidate → 389 docs/53 S2 provenance.)
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

`main` @ `1ad344b`, clean tree, only `main` branch. Recent merges (newest first):
`1ad344b` review digest → `5c4d00e` docs tidy → `7cd2ff0` survivor classify S2 →
`d361919` survivor classify S1 → invariant S3 → invariant S2 → invariant S1 →
retrieval S1-S3 → mock-smell S1 → run_pit sidecar → (run_kind + oracle + mutation arc).

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
- **DONE 2026-06-14 — #3 survived-mutant classification** (design `docs/49`): explain WHY a mutant
  survived (never assert equivalence — undecidable; never condemn a test).
  - **S1** (`app/mutation/survivors.py` `classify_survivors`): buckets non-killed mutants →
    `not_covered` / `survived_weak_oracle` / `survived_maybe_equivalent` / `survived_unclassified`
    + mutator explanation + `equivalence_likelihood`; matches the §16 `validate()` finding.
  - **S2**: invariant view attaches scoped classified survivors (`verified["survivors"]`);
    `run_case` puts whole-run survivors on `review_summary["mutation_survivors"]` (gated);
    `report_md` renders an advisory "Survived mutants" section. All advisory; verdict unchanged.
- **DONE 2026-06-14 — #6 badcase memory / retrieval** (design `docs/50`): judge-side precedent.
  - **S1** (`app/ledger/retrieval.py` `find_similar` / `find_similar_in_store`): explainable
    structural similarity over the ledger (same target/method/class, failure_type, business_pattern,
    fingerprint, repo — each with a reason); advisory, read-only, real records only, no embeddings.
  - **S2**: `JudgedRecord` gains DECLARED `root_cause`/`fix_note` (advisory, never fabricated);
    `find_similar` results carry the derived `signature` (`badcase_signature`) + the declared
    root-cause/fix → actionable precedent ("why" + "how"). Verdict unchanged.
  - **S3**: `find_similar(..., query_text=)` adds a **no-dependency** token-overlap (Jaccard,
    stdlib) over declared free-text (`reason: text_overlap`); explainable, never replaces structural
    signals. **Embedding retrieval stays DEFERRED** (new dep or API/cost → needs explicit approval).
- **DONE 2026-06-14 — #4 mock/external-dependency smell (judge-side slice)** (design `docs/51`):
  `app/quality/mock_smells.py` `detect_mock_smells` flags `mock_of_target` / `stub_returns_null` /
  `loose_matchers` / `real_dependency` (the gate already blocks sleep/random/time/IO). Surfaced as
  `review_summary["mock_smells"]` **after** the recommendation — advisory, **does NOT touch the
  quality gate**, changes no verdict. The generation-side **mock pattern library is deferred**.
- **DONE 2026-06-14 — #5 review digest (consolidation capstone)** (design `docs/52`):
  `app/review/review_digest.py` `build_review_digest` reads oracle-strength, mutation survivors,
  invariant verification, mock smells, quality-gate blockers from `review_summary` → a severity-sorted
  `{headline, flags:[{signal,severity,message}], flag_count}` checklist. Built twice: once in
  `generation_report` (per-candidate signals) and again in `runner._attach_digest` (after benchmark-
  layer signals). Computes nothing new; changes no recommendation/conclusion; `auto_accept_blocked`
  stays True. 9 tests. **Completes the value-judgment signal layer.**
- **DONE 2026-06-15 — submit_candidate S1 (judge any producer)** (design `docs/53`): closes the
  *"judge candidates from ANY producer"* gap — Claude/Codex/DeepSeek/human submissions now flow
  through the same judge stack. `POST /jobs/{id}/submit_candidate` →
  `app/pipeline/submit_pipeline.run_external_candidate` reuses target/context/preflight/write/
  execute/compare and feeds the same `assemble_generation_report` (no new judging logic).
  **Hard invariants forced at the boundary AND pipeline:** `run_kind="external"` (caller cannot
  override; generator path cannot claim it); `trusted=False`; `conclusion=NEED_HUMAN_REVIEW`;
  `producer_id` required + identifier-safe + not `"fake-1"` (impersonation guard, docs/43);
  `test_source` size-capped (256 KB); no LLM call; no production-code edits. New `JobStatus`:
  `SUBMIT_EXECUTE/SUBMIT_DONE/SUBMIT_FAILED`; on-disk file name `CalcSubmittedTest.java` distinct
  from the generator's `CalcAiGeneratedTest.java` so the two producer paths never collide. 33
  new tests; generator path unaffected.
- **DONE 2026-06-15 — submit_candidate S2 (provenance + charter invariant)** (design `docs/53` §9):
  audit found the analytics layer already supports `external` generically (`aggregate` /
  `_filter_kind` are `run_kind==<kind>` filters), so S2 = (a) `assemble_generation_report` surfaces
  `producer_id` + `run_kind` as top-level provenance (advisory; `trusted` stays `False`); (b) API
  whitespace-only `target_method`→`None` cleanup; (c) 8 tests proving "**external never enters the
  real headline**" (the parallel to "fake can never be real") on `aggregate()` + `aggregate_badcases()`
  + external-only view + report provenance. Benchmark `report_md` producer line deferred (external
  candidates don't flow through the benchmark runner yet). **S3 (manifest invariants + gated mutation
  on external candidates) designed, not started — needs approval.**
- **Deferred — do NOT start without explicit approval:** #6 embedding retrieval (dep/API); #4 mock
  pattern library (producer-side); #2 context retrieval, #5 multi-round repair; P3 /
  `submit_candidate`, Defects4J, multi-model.

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
