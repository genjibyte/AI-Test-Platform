"""run_kind: provenance of a generated-test candidate (P1-T3, docs/43, docs/53).

A generated test is tagged ``real`` / ``fake`` / ``dryrun`` / ``smoke`` / ``external``
at GENERATION (or SUBMIT) TIME by the producer -- never reconstructed from artifacts
or source text. Headline model-quality metrics use ``real`` only; the other kinds are
raw/audit counts.

Hard invariants (regression-tested):

- a fake client can never yield ``real``;
- a ``submit_candidate`` entry can never yield ``real`` or ``fake`` -- it is always
  ``external`` (docs/53); the caller cannot override.
"""
from __future__ import annotations

from typing import Optional

# Five kinds (owner decision, docs/43 §11.1 + docs/53). dryrun/smoke/external are
# NOT merged into fake; they are still excluded from headline model-quality metrics.
RUN_KINDS = ("real", "fake", "dryrun", "smoke", "external")
HEADLINE_KIND = "real"  # the only kind allowed into headline model-quality metrics
EXTERNAL_KIND = "external"  # producer-agnostic submit_candidate path (docs/53)


def resolve_run_kind(client_is_fake: bool, override: Optional[str] = None) -> str:
    """Decide a *generator*-path candidate's run_kind at generation time.

    - no override: a real client -> ``real``; a fake client -> ``fake``.
    - override (from the producer, e.g. a benchmark ``--run-kind`` flag) may set
      ``dryrun``/``smoke``/``fake``/``real``, but is validated and guarded.

    INVARIANTS:
    - a fake client can never be labeled ``real`` -- raises ``ValueError``.
    - ``external`` is reserved for ``submit_candidate``; the generator path cannot
      claim ``external`` -- raises ``ValueError``.
    """
    if override is not None:
        kind = override.strip().lower()
        if kind not in RUN_KINDS:
            raise ValueError(f"invalid run_kind {override!r}; must be one of {RUN_KINDS}")
        if kind == EXTERNAL_KIND:
            raise ValueError(
                "the generator path cannot claim run_kind='external' "
                "(reserved for submit_candidate, docs/53)"
            )
        if client_is_fake and kind == "real":
            raise ValueError(
                "fake client cannot be run_kind='real' (contamination guard, docs/43)"
            )
        return kind
    return "fake" if client_is_fake else "real"


def resolve_run_kind_for_submit(override: Optional[str] = None) -> str:
    """Decide a ``submit_candidate``-path candidate's run_kind (docs/53).

    The caller cannot override: ``submit_candidate`` is ALWAYS ``external``. Passing
    any non-``external`` value raises ``ValueError``. Rationale: a misleading
    ``run_kind`` is itself a form of producer hallucination; the entry point resists it.
    """
    if override is not None:
        kind = override.strip().lower()
        if kind != EXTERNAL_KIND:
            raise ValueError(
                f"submit_candidate run_kind must be '{EXTERNAL_KIND}', got {override!r} "
                "(caller cannot relabel an external submit; docs/53 §4)"
            )
    return EXTERNAL_KIND
