"""PIT (pitest-maven) command builder + XML report parser (docs/46 S3).

Pure + offline: this module can BUILD the Maven ``mutationCoverage`` goal (command-line,
**NO pom edit**) and PARSE PIT's ``mutations.xml``. It **NEVER runs Maven/PIT** -- running
mutation (which fetches the PIT plugin) is a separate, explicitly-enabled MANUAL benchmark
step. Mutation score is the real SEMANTIC oracle-strength signal (does the test kill
mutants?) and stays **ADVISORY** -- it never auto-accepts a candidate (docs/46 §2/§4).
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from collections import Counter
from typing import List, Optional

from pydantic import BaseModel, Field

# Pinned PIT plugin version -- fetched by Maven AT RUNTIME only when mutation is actually
# run (a manual step). This module adds no Python dependency and invokes nothing.
PIT_VERSION = "1.15.0"

# PIT statuses that count as "detected" (the test suite caught the mutant).
_DETECTED_STATUSES = {"KILLED", "TIMED_OUT"}


class MutationResult(BaseModel):
    """Parsed PIT report facts. ``available=False`` == no usable report -- treat like
    coverage_unavailable and NEVER block judging. ADVISORY only; carries no verdict."""

    available: bool = False
    total: int = 0
    detected: int = 0
    killed: int = 0
    survived: int = 0
    no_coverage: int = 0
    timed_out: int = 0
    mutation_score: Optional[float] = None     # detected / total (None when unavailable)
    status_counts: dict = Field(default_factory=dict)


def parse_pit_report(xml_text: Optional[str]) -> MutationResult:
    """Parse a PIT ``mutations.xml`` string into a MutationResult. Never raises; empty or
    malformed input -> ``available=False`` (mutation unavailable)."""
    if not xml_text or not xml_text.strip():
        return MutationResult(available=False)
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return MutationResult(available=False)
    muts = root.findall(".//mutation")
    total = len(muts)
    if total == 0:
        return MutationResult(available=False)
    status = Counter((m.get("status") or "UNKNOWN").upper() for m in muts)
    detected = sum(1 for m in muts if (m.get("detected") or "").strip().lower() == "true")
    return MutationResult(
        available=True,
        total=total,
        detected=detected,
        killed=status.get("KILLED", 0),
        survived=status.get("SURVIVED", 0),
        no_coverage=status.get("NO_COVERAGE", 0),
        timed_out=status.get("TIMED_OUT", 0),
        mutation_score=round(detected / total, 4),
        status_counts=dict(status),
    )


def build_pit_command(
    target_classes: str, target_tests: str, *, mvn: str = "mvn"
) -> List[str]:
    """Build the Maven ``mutationCoverage`` goal (command-line; **NO pom edit**) for a
    MANUAL run. This module never executes it -- docs/46 S3 stays dormant until enabled.

    ``target_classes`` / ``target_tests`` are PIT class globs (e.g. ``com.x.Calc``,
    ``com.x.CalcTest``). Configuration is passed via ``-D`` only, so the target repo's pom
    is never modified."""
    return [
        mvn,
        f"org.pitest:pitest-maven:{PIT_VERSION}:mutationCoverage",
        f"-DtargetClasses={target_classes}",
        f"-DtargetTests={target_tests}",
        "-DoutputFormats=XML",
        "-DtimestampedReports=false",
    ]
