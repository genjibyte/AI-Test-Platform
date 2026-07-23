# 51 — Mock / external-dependency smell detection (live contract, 2026-06-14)

> **Status: S1 implemented.** The judge-side advisory detector is live in
> `app/quality/mock_smells.py` and surfaced through `review_summary["mock_smells"]`,
> review digest flags, and Asset Gate inputs. It changes no quality-gate status,
> recommendation, conclusion, trusted state, executor, or dependency. The generation-side
> *mock pattern library* remains producer-side and deferred.

## 0. Why a SEPARATE detector (not a quality-gate change)
The quality gate (`app/quality/test_quality_gate.py`) already **blocks** the unstable/external
smells it owns — `Thread.sleep`, randomness, time (`System.currentTimeMillis`/`Instant.now`/…),
and IO/network (`new File`/`Paths.get`/`Files.`/`URL`/`URI`/`Socket`/`HttpClient`). We must **not**
change that judging logic. This judge-side slice is a **separate, advisory** detector covering
what the gate does *not*:

1. **Mock-framework smells** (Mockito) — a class of AI mistakes the gate ignores.
2. **Framework-level real dependencies** the gate's regex misses (JDBC / Spring / messaging).

It is surfaced for the human reviewer (like `oracle_strength_estimate`), never as a blocker.

## 1. Smells (static, regex-based; advisory — false positives possible by design)
- **`mock_of_target`** (high value): the test mocks the **class under test**
  (`mock(Target.class)` or `@Mock … Target`). Testing the mock, not the code — almost always
  worthless. Needs the target's simple class name.
- **`stub_returns_null`**: `thenReturn(null)` — stubbing null can mask NPE behaviour; review.
- **`loose_matchers`**: Mockito `any()` / `anyString()` / `anyInt()` … — loose stubbing that may
  not pin the real call.
- **`real_dependency`**: framework deps the gate misses — `DriverManager` / `getConnection`
  (JDBC), `RestTemplate` / `WebClient` / `JdbcTemplate` / `MongoClient` / `KafkaTemplate`,
  `@Autowired` (a real bean in a unit test). Advisory (the gate already blocks raw IO/Socket/HTTP).

Each finding: `{category, evidence, hint}`. Comments/strings are lightly stripped first to cut
false positives. Unknown / no smell -> empty.

## 2. Output + surface
`app/quality/mock_smells.py`:

```
detect_mock_smells(source, *, target_class=None) -> {
  "smells": [ {category, evidence, hint}, ... ],
  "counts": {mock_of_target, stub_returns_null, loose_matchers, real_dependency},
  "total": int,
  "advisory": True,
  "note": "static heuristic; advisory only -- a smell is a review hint, not a verdict",
}
```

Surfaced in `app/report/generation_report.py` as `review_summary["mock_smells"]`, added **after**
`recommend_with_reasons` (exactly like `oracle_strength_estimate`) so it changes no recommendation
or conclusion.

## 3. Scope guards — what this is NOT
- Not a quality-gate change: the gate is untouched; this is a parallel advisory signal.
- Not a verdict: never feeds `recommend_with_reasons`/`conclusion`; `auto_accept_blocked` stays
  True. A smell is a *review hint*, never a rejection.
- Not the mock **pattern library** (how to mock a Controller/Service/Repository) — that is
  generation-producer-side and out of scope here (deferred).
- No new dependency (stdlib `re`); static-only; never executes the test.

## 4. Slices
- **S1 — detector + surface (offline):** implemented. The four smells above +
  `detect_mock_smells` + `review_summary["mock_smells"]` wire-in. Pure, unit-tested.
- **S2 — (optional) deeper mock analysis:** wrong-type stub / unused mock / over-verification —
  harder + noisier; advisory only; needs its own design.

## 5. Acceptance — live
- `mock(Calc.class)` with `target_class=…Calc` -> `mock_of_target`; `thenReturn(null)` ->
  `stub_returns_null`; `any()` -> `loose_matchers`; `new RestTemplate()` -> `real_dependency`.
- A clean Mockito test (mocks a *collaborator*, stubs concretely, asserts) -> no smells.
- Smells appear in `review_summary["mock_smells"]` and change no `recommendation`/`conclusion`
  (regression-tested). The quality gate's own patterns are NOT duplicated here.

## 6. Relationship to siblings
The gate owns the IO/time/random *blockers*; `51` (this) adds the *mock-quality* review hints the
gate doesn't see; both compose with `46` (mutation) and `48`/`49` (invariant + survivor) to give
the reviewer a fuller picture — all advisory, none auto-accepting.

---

> Records a review-hint signal; grants no scope; changes no verdict. The product stays the
> **judgment** — here, *mock-quality smells for the reviewer* — not a green checkmark.
