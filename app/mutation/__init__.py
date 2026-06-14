"""Mutation-evidence subsystem (docs/46 S3) -- the real SEMANTIC oracle-strength signal.

DORMANT / offline core only: this package can BUILD a PIT (pitest-maven) Maven command and
PARSE a PIT XML report, but it NEVER invokes Maven/PIT itself. Actually running mutation
(which fetches the PIT plugin) is a separate, explicitly-enabled MANUAL benchmark step
(docs/46 §4/§8). Mutation evidence is ADVISORY -- it never auto-accepts a candidate, and
``conclusion`` stays ``NEED_HUMAN_REVIEW``.
"""
from app.mutation.pit import (
    JUNIT5_PLUGIN_VERSION,
    PIT_VERSION,
    MutationResult,
    build_pit_command,
    build_pit_pom,
    is_junit5_pom,
    parse_line_spec,
    parse_pit_report,
    scoped_mutation_score,
)
from app.mutation.run import run_pit

__all__ = [
    "JUNIT5_PLUGIN_VERSION",
    "PIT_VERSION",
    "MutationResult",
    "build_pit_command",
    "build_pit_pom",
    "is_junit5_pom",
    "parse_line_spec",
    "parse_pit_report",
    "scoped_mutation_score",
    "run_pit",
]
