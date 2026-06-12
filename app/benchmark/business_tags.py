"""Business-invariant tag vocabulary (docs/45 S1).

Advisory taxonomy: these tags ORGANIZE human review of a candidate test's business
value (KB docs/knowledge/INTERNET_TECH_BUSINESS_KB.md). They are **declared intent,
never verified value** (docs/45 §2) -- a tag never asserts the test is correct or
strong, only what business risk it is *supposed* to protect. The vocab is **non-
blocking**: an unknown value is allowed and must never fail generation or judging.
"""
from __future__ import annotations

from typing import Optional

# docs/45 §6 -- initial controlled vocab (extensible; "other"/"unknown" always allowed).
BUSINESS_DOMAINS = (
    "payments", "search", "recommendation", "ads", "ecommerce_marketplace",
    "logistics", "subscriptions", "trust_safety", "identity_access",
    "notifications", "experimentation", "reliability", "data_platform",
    "ai_ml_platform", "dev_productivity", "security_privacy", "other", "unknown",
)
BUSINESS_PATTERNS = (
    "idempotency", "state_transition", "eligibility", "ranking_stability",
    "metric_recompute", "fallback", "audit_trail", "access_control",
    "money_bound", "dedupe", "time_currency_boundary", "other", "unknown",
)
RISK_LEVELS = ("low", "medium", "high", "unknown")


def normalize_tag(value: Optional[str]) -> Optional[str]:
    """Lowercase + strip a tag; empty/None -> None. Never raises (non-blocking vocab)."""
    if value is None:
        return None
    v = value.strip().lower()
    return v or None


def is_known_domain(value: Optional[str]) -> bool:
    """Advisory predicate -- an unknown domain is allowed, just not a known one."""
    return normalize_tag(value) in BUSINESS_DOMAINS


def is_known_pattern(value: Optional[str]) -> bool:
    return normalize_tag(value) in BUSINESS_PATTERNS


def is_known_risk(value: Optional[str]) -> bool:
    return normalize_tag(value) in RISK_LEVELS
