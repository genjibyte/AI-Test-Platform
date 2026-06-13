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
# pitest-junit5-plugin -- required for PIT to discover JUnit 5 tests (docs/46 §14 finding).
JUNIT5_PLUGIN_VERSION = "1.2.1"

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


def is_junit5_pom(pom_text: Optional[str]) -> bool:
    """Heuristic: does this Maven pom use JUnit 5 (Jupiter)? PIT needs the
    pitest-junit5-plugin to discover tests for such targets (docs/46 §14)."""
    t = pom_text or ""
    return "junit-jupiter" in t or "org.junit.jupiter" in t


def _pit_plugin_xml(
    target_classes: str, target_tests: str, *, junit5: bool, pit_version: str, junit5_version: str
) -> str:
    dep = ""
    if junit5:
        dep = (
            "      <dependencies>\n"
            "        <dependency>\n"
            "          <groupId>org.pitest</groupId>\n"
            "          <artifactId>pitest-junit5-plugin</artifactId>\n"
            f"          <version>{junit5_version}</version>\n"
            "        </dependency>\n"
            "      </dependencies>\n"
        )
    return (
        "    <plugin>\n"
        "      <groupId>org.pitest</groupId>\n"
        "      <artifactId>pitest-maven</artifactId>\n"
        f"      <version>{pit_version}</version>\n"
        f"{dep}"
        "      <configuration>\n"
        f"        <targetClasses><param>{target_classes}</param></targetClasses>\n"
        f"        <targetTests><param>{target_tests}</param></targetTests>\n"
        "        <outputFormats><param>XML</param></outputFormats>\n"
        "        <timestampedReports>false</timestampedReports>\n"
        "      </configuration>\n"
        "    </plugin>\n"
    )


def build_pit_pom(
    pom_text: str,
    *,
    target_classes: str,
    target_tests: str,
    junit5: Optional[bool] = None,
    pit_version: str = PIT_VERSION,
    junit5_version: str = JUNIT5_PLUGIN_VERSION,
) -> str:
    """docs/46 §14 (JUnit5-aware): return a SIDECAR pom -- the original plus the
    pitest-maven plugin (and pitest-junit5-plugin for JUnit 5) -- so PIT can run on JUnit 5
    targets WITHOUT editing the original pom (write it as a separate file and run
    ``mvn -f``). ``junit5`` is auto-detected when ``None``. Pure text injection
    (namespace-agnostic); offline; runs nothing."""
    if junit5 is None:
        junit5 = is_junit5_pom(pom_text)
    block = _pit_plugin_xml(
        target_classes, target_tests, junit5=junit5,
        pit_version=pit_version, junit5_version=junit5_version,
    )
    if "</plugins>" in pom_text:
        return pom_text.replace("</plugins>", block + "  </plugins>", 1)
    if "</build>" in pom_text:
        return pom_text.replace("</build>", f"  <plugins>\n{block}  </plugins>\n  </build>", 1)
    if "</project>" in pom_text:
        return pom_text.replace(
            "</project>", f"  <build>\n  <plugins>\n{block}  </plugins>\n  </build>\n</project>", 1
        )
    return pom_text
