"""Phase 2.5 — real-model x real-repo mini-benchmark harness.

Runs the existing Phase 1 judge + Phase 2 generate pipelines over real open
source Maven repositories and records facts per docs/07 §8. Adds NO new judging
logic — it only orchestrates and aggregates. The LLM client is whatever is
configured (offline fake by default; a real provider when env is set), so the
harness can be validated on real repos offline before spending on a real model.
"""

from app.benchmark.validation_line import (
    HUMAN_LABEL_READINESS_VERSION,
    human_label_metric_readiness,
    validation_line_summary,
)
from app.benchmark.manifest_governance import (
    GOLDEN_DEFECT_DENOMINATOR_READINESS_VERSION,
    golden_defect_denominator_readiness,
)

__all__ = [
    "GOLDEN_DEFECT_DENOMINATOR_READINESS_VERSION",
    "HUMAN_LABEL_READINESS_VERSION",
    "golden_defect_denominator_readiness",
    "human_label_metric_readiness",
    "validation_line_summary",
]
