"""Read-only benchmark audit (P1-T4 + P1-T3 run_kind, foundation hardening).

Recomputes the headline benchmark numbers from local ``var/benchmark/*/bench.db``
artifacts using the pure ``assemble_generation_report`` -- NO model/API calls, NO
``.env`` reading, NO mutation of any data.

run_kind (docs/43): this script **prefers the authoritative ``run_kind`` field** when a
row carries it, and falls back to a clearly-labeled HEURISTIC for historical rows that
have no field. Headline model-quality metrics use ``run_kind == "real"`` only;
``fake``/``dryrun``/``smoke`` and unknown rows are raw/audit counts.

LIMITATION: until benchmarks are re-run so every row carries ``run_kind``, the fake/real
split for historical rows is heuristic and incomplete. This script never mutates
historical ``bench.db`` (owner decision: historical data stays read-only).

Usage (venv python, from repo root):
    & "E:\\AI-Test-Platform\\.venv\\Scripts\\python.exe" scripts/audit_bench.py
    & "...python.exe" scripts/audit_bench.py --dir var/benchmark
"""
from __future__ import annotations

import argparse
import glob
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

# Make ``app`` importable when run as ``python scripts/audit_bench.py`` from the repo
# root. assemble_generation_report is pure shaping; it never instantiates Settings and
# therefore never reads ``.env``.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.llm.run_kind import RUN_KINDS  # noqa: E402
from app.report.generation_report import assemble_generation_report  # noqa: E402

_FAKE_MARKER = "FAKE CLIENT PLACEHOLDER"
_COMPILED = {"PASS", "TEST_FAILURE", "NO_TESTS"}  # platform `compiled` definition


def _heuristic_fake(gen: dict, rep: dict) -> bool:
    """Historical-only fallback. NOT authoritative -- see module LIMITATION."""
    src = (
        (gen.get("write") or {}).get("content")
        or (gen.get("result") or {}).get("test_source")
        or ""
    )
    return (_FAKE_MARKER in src) or ((rep.get("model") or "") == "fake-1")


def _load(bench_dir: Path):
    dbs = sorted(glob.glob(str(bench_dir / "*" / "bench.db")))
    rows = []
    for db in dbs:
        run = Path(db).parent.name
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        try:
            for r in conn.execute("SELECT generation_json FROM jobs"):
                if not r["generation_json"]:
                    continue
                gen = json.loads(r["generation_json"])
                rep = assemble_generation_report(gen)
                if rep.get("gen_outcome") is None:
                    continue
                rk = gen.get("run_kind")
                rk = rk if rk in RUN_KINDS else None  # authoritative field, if valid
                rows.append(
                    {
                        "run": run,
                        "outcome": rep.get("gen_outcome"),
                        "quality": (rep.get("quality_gate") or {}).get("status"),
                        "rec": rep.get("review_recommendation"),
                        "run_kind": rk,  # None == historical / no field
                        "heuristic_fake": _heuristic_fake(gen, rep),
                    }
                )
        except sqlite3.Error as exc:
            print(f"WARN: skipping {db}: {exc}", file=sys.stderr)
        finally:
            conn.close()
    return dbs, rows


def _summary(label: str, rows: list) -> None:
    n = len(rows)
    print(f"\n=== {label} (n={n}) ===")
    if not n:
        print("  (no rows)")
        return
    oc = Counter(r["outcome"] for r in rows)
    q = Counter(r["quality"] for r in rows if r["quality"])
    rec = Counter(r["rec"] for r in rows if r["rec"])
    compiled = sum(1 for r in rows if r["outcome"] in _COMPILED)
    passed = oc.get("PASS", 0)
    ct: dict = defaultdict(Counter)
    for r in rows:
        ct[r["outcome"]][r["quality"]] += 1
    green = ct.get("PASS", Counter())
    print(f"  outcome  : {dict(oc.most_common())}")
    print(f"  quality  : {dict(q.most_common())}")
    print(f"  recommend: {dict(rec.most_common())}")
    print(f"  compiled (strict {{PASS,TEST_FAILURE,NO_TESTS}}) = {compiled}/{n} = {compiled / n:.1%}")
    print(f"  passed (PASS)                                  = {passed}/{n} = {passed / n:.1%}")
    print(
        f"  PASS x quality = {{PASS:{green['PASS']}, REVIEW:{green['REVIEW']}, "
        f"FAIL:{green['FAIL']}}}  (green-but-quality-FAIL = {green['FAIL']}/{sum(green.values())})"
    )


def main(argv: list) -> int:
    ap = argparse.ArgumentParser(description="Read-only benchmark audit (P1-T4 / run_kind)")
    ap.add_argument(
        "--dir", default="var/benchmark", help="benchmark root (default: var/benchmark)"
    )
    args = ap.parse_args(argv)

    bench_dir = Path(args.dir)
    if not bench_dir.is_dir():
        print(f"ERROR: benchmark dir not found: {bench_dir.resolve()}", file=sys.stderr)
        return 2
    dbs, rows = _load(bench_dir)
    if not dbs:
        print(
            f"ERROR: no bench.db under {bench_dir.resolve()}{chr(92)}*{chr(92)}bench.db",
            file=sys.stderr,
        )
        return 2

    authoritative = [r for r in rows if r["run_kind"] is not None]
    unknown = [r for r in rows if r["run_kind"] is None]
    print(f"bench.db files : {len(dbs)}   generation rows : {len(rows)}")
    print(f"  authoritative run_kind present : {len(authoritative)}")
    print(f"  historical / no run_kind       : {len(unknown)}  (classified heuristically)")
    print(f"  authoritative run_kind dist    : {dict(Counter(r['run_kind'] for r in authoritative))}")
    print(
        "  heuristic (unknown rows)       : "
        f"{dict(Counter('fake' if r['heuristic_fake'] else 'real' for r in unknown))}"
    )
    print(
        "  fake-ish by run (heuristic)    : "
        f"{dict(Counter(r['run'] for r in unknown if r['heuristic_fake']))}"
    )

    _summary("RAW (all rows, all kinds)", rows)
    _summary(
        "HEADLINE -- REAL only (authoritative run_kind == real)",
        [r for r in rows if r["run_kind"] == "real"],
    )
    _summary(
        "HISTORICAL fallback -- REAL (heuristic, unknown provenance, NOT authoritative)",
        [r for r in unknown if not r["heuristic_fake"]],
    )

    print(
        f"\nLIMITATION: {len(authoritative)}/{len(rows)} rows carry an authoritative "
        f"run_kind (docs/43); {len(unknown)} are historical (no field) and split "
        'heuristically ("FAKE CLIENT PLACEHOLDER" / model == "fake-1"), which is '
        "incomplete.\nHeadline model-quality metrics use authoritative run_kind == real "
        "only; fake/dryrun/smoke and unknown rows are raw/audit counts. Re-run "
        "benchmarks so new rows carry run_kind. Historical bench.db is never mutated."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
