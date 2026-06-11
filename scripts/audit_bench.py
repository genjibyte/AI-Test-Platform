"""Read-only benchmark audit (P1-T4, foundation hardening).

Recomputes the headline benchmark numbers from local ``var/benchmark/*/bench.db``
artifacts using the pure ``assemble_generation_report`` -- NO model/API calls, NO
``.env`` reading, NO mutation of any data. It separates fake/dry-run placeholder rows
from real-model rows so headline metrics are not silently contaminated (the docs/42
incident, n=80 raw -> n=67 real).

LIMITATION: the benchmark schema has no explicit ``run_kind`` field, so the fake/real
split here is HEURISTIC (the ``FAKE CLIENT PLACEHOLDER`` marker in ``test_source`` or
``model == "fake-1"``), not authoritative. P1-T3 should add a real ``run_kind``. This
script must not pretend the heuristic is complete.

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
from app.report.generation_report import assemble_generation_report  # noqa: E402

_FAKE_MARKER = "FAKE CLIENT PLACEHOLDER"
_COMPILED = {"PASS", "TEST_FAILURE", "NO_TESTS"}  # platform `compiled` definition


def _is_fake(gen: dict, rep: dict) -> bool:
    """Heuristic only -- see module LIMITATION. Not a substitute for a run_kind field."""
    src = (
        (gen.get("write") or {}).get("content")
        or (gen.get("result") or {}).get("test_source")
        or ""
    )
    if _FAKE_MARKER in src:
        return True
    return (rep.get("model") or "") == "fake-1"


def _load(bench_dir: Path):
    dbs = sorted(glob.glob(str(bench_dir / "*" / "bench.db")))
    rows = []
    for db in dbs:
        run = Path(db).parent.name
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.execute("SELECT generation_json FROM jobs")
            for r in cur:
                if not r["generation_json"]:
                    continue
                gen = json.loads(r["generation_json"])
                rep = assemble_generation_report(gen)
                if rep.get("gen_outcome") is None:
                    continue
                rows.append(
                    {
                        "run": run,
                        "outcome": rep.get("gen_outcome"),
                        "quality": (rep.get("quality_gate") or {}).get("status"),
                        "rec": rep.get("review_recommendation"),
                        "fake": _is_fake(gen, rep),
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
    ap = argparse.ArgumentParser(description="Read-only benchmark audit (P1-T4)")
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

    fake = [r for r in rows if r["fake"]]
    real = [r for r in rows if not r["fake"]]
    print(f"bench.db files : {len(dbs)}   generation rows : {len(rows)}")
    print(f"  fake/dry-run (heuristic): {len(fake)}   real-model (heuristic): {len(real)}")
    print(f"  fake by run : {dict(Counter(r['run'] for r in fake))}")

    _summary("RAW (all rows, incl. fake)", rows)
    _summary("REAL-MODEL ONLY (heuristic)", real)

    print(
        "\nLIMITATION: current benchmark schema lacks explicit run_kind; fake/real"
        "\nseparation is therefore heuristic or incomplete until P1-T3 is implemented."
        '\n(heuristic = "FAKE CLIENT PLACEHOLDER" in test_source OR model == "fake-1")'
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
