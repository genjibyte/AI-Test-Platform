"""Business-invariant tag vocabulary (docs/50_benchmark/45 S1).

Advisory taxonomy: these tags ORGANIZE human review of a candidate test's business
value. They are **declared intent, never verified value**; a tag never asserts the
test is correct or strong, only what business risk it is *supposed* to protect. The
vocab is **non-blocking**: an unknown value is allowed and must never fail generation
or judging.
"""
from __future__ import annotations

from typing import Optional

# docs/50_benchmark/45 S6 -- initial controlled vocab (extensible; "other"/"unknown" always allowed).
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


def business_review_rubric(
    *,
    business_domain: Optional[str] = None,
    business_pattern: Optional[str] = None,
    expected_invariant: Optional[str] = None,
    risk_level: Optional[str] = None,
    declared_invariant: Optional[str] = None,
) -> dict:
    """docs/50_benchmark/45 S3: an ADVISORY human-review rubric.

    Surfaces the case-level (authoritative) business invariant a candidate is *supposed*
    to protect, an explicitly-UNTRUSTED model-declared invariant, and the fields a human
    reviewer fills in. It is NOT a verdict: it never accepts/scores a candidate and never
    changes the recommendation/conclusion (auto_accept stays blocked; docs/50_benchmark/45
    S2/S10).
    """
    return {
        # authoritative (manifest/human): what risk the target is supposed to protect
        "business_domain": normalize_tag(business_domain),
        "business_pattern": normalize_tag(business_pattern),
        "expected_invariant": expected_invariant,
        "risk_level": normalize_tag(risk_level),
        # an unverified model claim -- NEVER trusted (anti-hallucination)
        "declared_invariant": declared_invariant,
        "declared_invariant_trusted": False,
        # the human reviewer fills these (advisory; the platform does NOT compute them)
        "risk_covered": None,
        "oracle_strength": None,
        "fake_green_risk": None,
        "human_review_note": None,
        # invariant: a business tag never accepts a candidate
        "auto_accept_blocked": True,
    }
