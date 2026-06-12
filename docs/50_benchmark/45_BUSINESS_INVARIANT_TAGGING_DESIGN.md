# Business-invariant tagging — design

> Date: 2026-06-12. **DESIGN ONLY. NOT implemented.** No code, no model, no benchmark,
> no data mutation. The `run_kind` follow-up promised in `docs/50_benchmark/43_RUN_KIND_DESIGN.md`
> §7 ("a separate, later field set"). This doc locks down *what* to build so the eventual
> change is small, bounded, and reviewable — and so it cannot become a fake semantic signal.
>
> Upstream: `docs/knowledge/INTERNET_TECH_BUSINESS_KB.md` (§2 domain map, §19 domain→pattern
> matrix, §20.2 field set, §22 candidate invariants, §23 operating principle); thesis
> `docs/00_foundation/40_CORE_THESIS_REPOSITIONING.md`; charter `docs/00_foundation/00_PROJECT_CHARTER.md`.

## 0. Why

Structural quality is already gated (assertion presence/shape → quality gate). **Semantic
value — whether a candidate test protects a meaningful business invariant — is not modeled
at all.** Today the ledger cannot tell apart a test that protects *"the same idempotency key
must not create a duplicate charge"* from one that asserts `assertNotNull(result)`: both are
just `PASS` rows.

KB §23 states the operating principle: business knowledge is a **filter for human review** —
*"Does this generated test protect a meaningful business invariant? If no, it is not strong
even if it passes."* The goal here is a small, **source-agnostic metadata** field set that
records *what business risk a candidate is supposed to protect*, so reports / ledger / review
can be organized by business value — **without auto-judging that value** (judging stays human
review, conclusion stays `NEED_HUMAN_REVIEW`).

## 1. The fields

```
business_domain     ∈ controlled vocab (§6) | "other" | "unknown"   # which business area
business_pattern    ∈ controlled vocab (§6) | "other" | "unknown"   # which risk shape
expected_invariant  : free-text, one line, human-readable           # the protected rule
risk_level          ∈ { low, medium, high, unknown }   (optional)   # business stakes
```

`expected_invariant` example (KB §22): *"Retrying the same payment request with the same
idempotency key must not create a duplicate charge."*

## 2. The load-bearing distinction — declared **intent**, not verified **value** (anti-hallucination)

This is the crux and the reason the field set is risky if done naively. **A business tag is a
candidate claim about what a test *should* protect; it is never proof that the test protects
it.** The platform's whole identity is resisting fake/green-but-empty tests, so a tag must
never become a confident-sounding but unverified value signal.

Two trust levels, kept strictly separate:

- **case-level (authoritative):** tags set on the benchmark *case / target* by the manifest
  author (a human). This is trustworthy **intent** — "this target is about payment
  idempotency." It describes the code-under-test, not the candidate's correctness.
- **candidate-declared (untrusted):** if a model/agent declares its own `expected_invariant`
  for the test it wrote, that is an **unverified claim the model can hallucinate**. It is
  suffixed `_declared`, surfaced for human review **only**, **never** aggregated as fact, and
  **never** feeds any accept/score path.

Whether the test *actually* protects the invariant is **not auto-decidable** — that is the
semantic-oracle-strength gap (see §15, a separate deferred design). Tags **frame** that
judgment for the human; they do **not** close it. This mirrors the thesis exactly: a declared
business invariant is a *candidate*, judged not trusted — like the test itself.

## 3. Where it is set (single source of truth)

**Decided by the producer at definition time — never reconstructed from artifacts/source by
the pipeline** (same rule as `run_kind`, docs/43 §2):

- The benchmark **manifest** (`BenchCase`) carries the authoritative tags; the manifest author
  (human) sets them per target.
- An optional model-`*_declared` invariant may be captured in the generation report for the
  review rubric (§5) — clearly marked untrusted, never authoritative.
- The pipeline must **not** infer tags from source/artifact text.

## 4. How it threads (read-only carry — no judging change)

One optional field group, copied forward, touching no compile/quality/review/repair logic
(same shape as `run_kind`, docs/43 §3):

- `BenchCase.business_domain / business_pattern / expected_invariant / risk_level` (all `Optional`).
- `BenchCaseResult` carries them (copied from the case).
- `JudgedRecord` carries them (copied on ingest) — **source-agnostic**: works for human /
  external-agent / platform-generator authors alike.
- `assemble_generation_report` passes them through read-only.

No change to `gen_outcome`, quality gate, review policy, preflight, or repair.

## 5. Queries / review (descriptive in v1, advisory only)

- **Group-by:** benchmark report + ledger analytics can group counts by `business_domain` /
  `business_pattern`, answering KB §20.2's question *"what business risk did the candidate
  protect?"* instead of only *"did it pass?"*.
- **Review rubric (KB §20.4):** surface `expected_invariant` (+ the untrusted
  `*_declared` one) into `review_summary` so a human reviewer sees, per candidate:
  `business_invariant / risk_covered / oracle_strength / fake_green_risk / human_review_note`
  — all **advisory**, the human fills/decides.
- **v1 does NOT change the recommendation algorithm.** A high-value tag must **not**
  auto-raise `STRONG` (that would reward a possibly-hallucinated tag). Any "reward business
  invariants" signal (KB §20.1) is a **separate, later, carefully-guarded** slice (§14 open
  decision 3).

## 6. Controlled vocabularies (initial, from the KB — advisory taxonomy, extensible)

- `business_domain`: `payments`, `search`, `recommendation`, `ads`, `ecommerce_marketplace`,
  `logistics`, `subscriptions`, `trust_safety`, `identity_access`, `notifications`,
  `experimentation`, `reliability`, `data_platform`, `ai_ml_platform`, `dev_productivity`,
  `security_privacy`, `other`, `unknown`. (KB §2)
- `business_pattern`: `idempotency`, `state_transition`, `eligibility`, `ranking_stability`,
  `metric_recompute`, `fallback`, `audit_trail`, `access_control`, `money_bound`, `dedupe`,
  `time_currency_boundary`, `other`, `unknown`. (KB §19 / §20.2)
- `risk_level`: `low`, `medium`, `high`, `unknown`.
- `expected_invariant`: free-text one-liner (KB §22 examples).

`other` / `unknown` are always allowed; the vocab is a **non-blocking** label — an unknown
value must never fail generation or judging.

## 7. Backward compatibility / historical data

Historical `bench.db` rows and existing manifests carry **no** tags → **unknown**. **No
backfill** (same discipline as `run_kind` D-003, docs/44). Any group-by-pattern view counts
only tagged rows; untagged rows go to an explicit `unknown` bucket, clearly labeled. Historical
artifacts stay read-only.

## 8. Interaction with `run_kind` (compose, do not conflate)

Orthogonal axes: business tags describe **what risk**; `run_kind` describes **real vs
fake/dryrun/smoke**. A headline business-pattern *model-quality* view must still default to
`run_kind == "real"` (run_kind S2): a fake/dryrun row's business tag is **not** model-quality
evidence. The two filters compose (real ∩ business_pattern), never substitute.

## 9. Regression tests (when implemented)

- tags carried read-only `case → result → record`;
- a `*_declared` (untrusted) tag is **never** folded into an authoritative aggregate;
- `conclusion` / `trusted` / `accept_rate` unchanged by the presence of any tag;
- a tagged group-by excludes untagged rows from the tagged view (labeled `unknown`), and
  composes with `run_kind == real`.

## 10. Scope guard — what NOT to do

- **No auto-scoring / auto-accept / auto-reward from tags.** `conclusion` stays
  `NEED_HUMAN_REVIEW`, `trusted = False`. A tag is descriptive, not a verdict.
- **No claim that a tag verifies semantic value** — that is the deferred oracle-strength work
  (§15). Do not let a tag imply the test is correct or strong.
- The pipeline must not infer tags from source text (only a human/manifest sets authoritative
  tags; only an explicitly-untrusted path records a model-declared one).
- No real-bug / Defects4J / mutation benchmark; no multi-model experiment; no new dependency.
- Design-only now; implement later as a small `run_kind`-style slice **on explicit approval**.

## 11. Files likely touched (when implemented — NOT now)

- `app/benchmark/models.py` — `BenchCase` + `BenchCaseResult` fields; optional group-by in
  `aggregate()` (compose with the `run_kind` filter).
- benchmark manifest loader (`load_spec`) — accept the optional tag fields.
- `app/benchmark/report_md.py` — group-by rows (descriptive).
- `app/ledger/{models,ingest,analytics}.py` — `JudgedRecord` fields + group-by views.
- `app/report/generation_report.py` — surface `expected_invariant` + the untrusted
  `*_declared` into `review_summary` (advisory).
- `scripts/run_benchmark.py` / `scripts/audit_bench.py` — optional group-by (read-only).
- a small vocab module (e.g. `app/benchmark/business_tags.py`, like `app/llm/run_kind.py`).
- `tests/` — the regression tests (§9).

## 12. Rollout (small, independently testable slices)

- **S1 — schema + set on manifest + carry read-only.** Add the fields, set from the manifest,
  thread `case → result → record`. No query change.
- **S2 — descriptive group-by.** Reports / ledger group by domain/pattern; compose with
  `run_kind == real` for model-quality views.
- **S3 — review rubric surfacing.** Put `expected_invariant` (+ untrusted `*_declared`) into
  `review_summary`; add regression tests. Still advisory, human-review.
- **(Deferred, separate, guarded)** any recommendation-signal use of tags (§14 decision 3),
  only after the oracle-strength design lands.

Each slice is small and paused until approved.

## 13. Acceptance (when implemented)

`pytest` green incl. new tests; `conclusion` / `trusted` / `accept_rate` unchanged; tags
carried `case → result → record`; a `*_declared` tag never becomes authoritative; group-by
works and composes with `run_kind == real`; no judging-logic change.

## 14. Open decisions for the owner

1. **Field names.** docs/43 §7 named `expected_invariant`; KB §20.2 named
   `expected_business_invariant` + `risk_level`. Recommend: `expected_invariant` + optional
   `risk_level` (four fields), matching docs/43 §7.
2. **Capture model-`declared` invariant in v1, or case-level (human) tags only?** Recommend:
   case-level authoritative now; capture the untrusted `*_declared` only in S3's rubric.
3. **May a tag ever influence the recommendation (KB §20.1)?** Recommend: **No** in v1
   (descriptive only). Revisit as a separate guarded slice **after** the oracle-strength work,
   to avoid rewarding a hallucinated tag.
4. **Vocabulary granularity** (full 16-domain map vs a short list). Recommend: start with §6,
   with `other` / `unknown` always allowed and the vocab non-blocking.

## 15. Relationship to the deferred semantic-oracle-strength work

Tags **frame** the question (*"this should protect invariant X"*); a future oracle-strength
signal (a separate advisory, human-review design) would assess **how strongly** the test
actually checks it. Tags alone = organized human review; tags + oracle-strength = the full
semantic-value picture. **Neither auto-accepts.** This design deliberately stops at framing.

---

> This design records the field set it adds; it grants no new scope and changes no judging
> logic. The project stays: *AI-generated test candidate evaluation / audit / engineering-
> usability platform* — KB §23: do **not** broaden into a generic internet-business platform;
> use this only to organize human review of test value.
