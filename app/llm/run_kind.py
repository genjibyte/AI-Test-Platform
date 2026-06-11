"""run_kind: provenance of a generated-test candidate (P1-T3, docs/43).

A generated test is tagged ``real`` / ``fake`` / ``dryrun`` / ``smoke`` at GENERATION
TIME by the producer -- never reconstructed from artifacts or source text. Headline
model-quality metrics use ``real`` only; ``fake``/``dryrun``/``smoke`` are raw/audit
counts.

Hard invariant (regression-tested): **a fake client can never yield ``real``.**
"""
from __future__ import annotations

from typing import Optional

# The four kinds are kept distinct (owner decision, docs/43 §11.1). dryrun/smoke are
# NOT merged into fake; they are still excluded from headline model-quality metrics.
RUN_KINDS = ("real", "fake", "dryrun", "smoke")
HEADLINE_KIND = "real"  # the only kind allowed into headline model-quality metrics


def resolve_run_kind(client_is_fake: bool, override: Optional[str] = None) -> str:
    """Decide a candidate's run_kind at generation time.

    - no override: a real client -> ``real``; a fake client -> ``fake``.
    - override (from the producer, e.g. a benchmark ``--run-kind`` flag) may set
      ``dryrun``/``smoke``/``fake``/``real``, but is validated and guarded.

    INVARIANT: a fake client can never be labeled ``real`` -- raises ``ValueError``.
    """
    if override is not None:
        kind = override.strip().lower()
        if kind not in RUN_KINDS:
            raise ValueError(f"invalid run_kind {override!r}; must be one of {RUN_KINDS}")
        if client_is_fake and kind == "real":
            raise ValueError(
                "fake client cannot be run_kind='real' (contamination guard, docs/43)"
            )
        return kind
    return "fake" if client_is_fake else "real"
