"""Phase 2.5 — real-model x real-repo mini-benchmark harness.

Runs the existing Phase 1 judge + Phase 2 generate pipelines over real open
source Maven repositories and records facts per docs/07 §8. Adds NO new judging
logic — it only orchestrates and aggregates. The LLM client is whatever is
configured (offline fake by default; a real provider when env is set), so the
harness can be validated on real repos offline before spending on a real model.
"""
