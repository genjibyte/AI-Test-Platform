"""Phase 2.5 mini-benchmark CLI.

Runs the benchmark over a spec of real Maven repos and writes report.json +
report.md. The LLM client is whatever is configured via env (offline fake by
default; a real provider when TESTAGENT_LLM_* is set).

Usage::

    set TESTAGENT_MAVEN_CMD=C:\\path\\to\\mvn.cmd
    # offline dry-run on real repos (no key, placeholder tests):
    python -m scripts.run_benchmark benchmarks/spec.example.json --out var/benchmark/dryrun

    # formal run with a real model:
    set TESTAGENT_LLM_PROVIDER=deepseek
    set TESTAGENT_LLM_MODEL=deepseek-v4-pro
    set TESTAGENT_LLM_API_KEY=...
    python -m scripts.run_benchmark benchmarks/spec.example.json --out var/benchmark/deepseek
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.benchmark.models import load_spec
from app.benchmark.report_md import render_markdown
from app.benchmark.runner import run_benchmark


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Phase 2.5 mini-benchmark")
    parser.add_argument("spec", help="path to a benchmark spec JSON")
    parser.add_argument("--out", default="var/benchmark/run", help="output directory")
    args = parser.parse_args(argv)

    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    cases = load_spec(spec)
    out = Path(args.out)

    report = run_benchmark(cases, workdir=out)

    (out / "report.json").write_text(
        report.model_dump_json(indent=2), encoding="utf-8"
    )
    md = render_markdown(report)
    (out / "report.md").write_text(md, encoding="utf-8")

    print(md)
    print(f"\nwrote {out / 'report.json'} and {out / 'report.md'}")
    a = report.aggregate
    # nonzero exit if nothing was even judged, so CI/scripts can detect a dud run
    return 0 if a.get("buildable_repos", 0) > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
