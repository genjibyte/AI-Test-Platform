# Internet & Technology Business Knowledge Base

## Purpose

This document summarizes reusable business-domain knowledge across the internet and technology industry.

It is not internship-specific.
It is not a generic business overview.
It is an operational knowledge base for this project:

```text
AI-generated test candidate evaluation / audit / engineering-usability platform
```

The goal is to help coding agents, reviewer agents, and future benchmark designers understand what real internet/tech systems care about:

* business entities
* critical user journeys
* quality risks
* product metrics
* testable invariants
* failure modes
* benchmark scenario ideas
* how generated tests can be judged for business value

The core principle:

```text
A generated test is valuable only if it protects a meaningful business invariant.
```

A test that merely compiles and passes is not enough.

---

# 1. Cross-Industry Thesis

## 1.1 Most internet businesses are optimization systems

Modern internet companies are not just CRUD systems. They are large-scale optimization systems.

Common optimization targets include:

* user engagement
* conversion
* retention
* revenue
* fulfillment quality
* safety
* trust
* latency
* reliability
* cost efficiency
* compliance
* marketplace balance
* model quality
* operational efficiency

A generated test candidate should be judged by whether it protects a meaningful optimization boundary.

Bad generated test:

```text
assertNotNull(result)
```

Better generated test:

```text
when payment is retried with the same idempotency key,
the system must not create a duplicate charge.
```

---

## 1.2 Business logic usually lives in state transitions and trade-offs

The most valuable tests usually target:

* order state transitions
* payment state transitions
* refund and dispute flows
* inventory reservation and release
* user permission changes
* fraud/risk decisions
* ranking eligibility
* matching and dispatch constraints
* experiment assignment
* notification delivery guarantees
* quota/rate-limit behavior
* privacy and consent boundaries
* rollback and recovery behavior

The project should prioritize generated tests that exercise these boundaries.

---

## 1.3 Metrics are part of the business logic

Internet systems are judged by metrics, not just functional correctness.

A feature may be functionally correct but still bad if it harms:

* latency
* conversion
* cancellation rate
* fulfillment rate
* ranking relevance
* abuse rate
* payment acceptance
* fraud loss
* user trust
* operational cost
* error budget
* data quality
* experiment validity

Project implication:

QualityGate should eventually distinguish:

```text
functional correctness
business invariant protection
metric-sensitive risk
operational risk
compliance risk
```

---

# 2. Industry Domain Map

The internet/tech industry can be grouped into recurring business domains.

## Major domains

1. Search and discovery
2. Recommendation and feed ranking
3. Advertising and monetization
4. E-commerce and marketplace
5. Logistics and dispatch
6. Payments and fintech
7. Subscriptions and billing
8. Trust and safety
9. Identity, account, and access
10. Notifications and messaging
11. Experimentation and analytics
12. Reliability and release engineering
13. Data platform and reporting
14. AI/ML platform and model governance
15. Developer productivity and coding agents
16. Security, privacy, and compliance

Each domain has its own quality risks and test patterns.

---

# 3. Search and Discovery

## Business purpose

Search helps users express intent and find relevant items, content, people, merchants, jobs, or knowledge.

Typical products:

* Google Search
* Etsy Search
* LinkedIn Search
* Spotify Search
* e-commerce product search
* local search
* help-center search
* internal knowledge search

## Core entities

* query
* user
* document / item / listing
* index
* candidate set
* ranker
* filters
* facets
* personalization features
* relevance score
* click / conversion / dwell signal

## Critical business metrics

* query success rate
* click-through rate
* conversion rate
* zero-result rate
* reformulation rate
* latency
* relevance score
* result diversity
* seller/item exposure
* abuse/spam rate
* user satisfaction

## Common failure modes

* query returns irrelevant results
* exact match works but semantic intent fails
* synonyms and typos are not handled
* filters remove too many valid results
* ranking favors stale or low-quality content
* personalization overfits and hurts exploration
* search latency increases
* sponsored results harm organic relevance
* bad query understanding causes business loss
* LLM-generated query expansion changes intent incorrectly

## Testable invariants

* empty query should not crash the search path
* invalid filters should be rejected or ignored safely
* pagination must be stable across requests
* ranking should be deterministic under fixed seed/features
* blocked or unavailable items must not appear
* user-private or restricted items must not appear
* sponsored/organic separation must be explicit
* query normalization must preserve intent
* feature fallback must work when personalization features are missing

## Project implication

Search-related generated tests should not only assert that a result list exists. They should check:

* filtering correctness
* eligibility rules
* ranking stability
* fallback behavior
* restricted-content exclusion
* pagination invariants
* semantic-intent boundaries

## Benchmark scenario ideas

* query normalization unit tests
* filter/facet combination tests
* ranking tie-breaker tests
* restricted item exclusion tests
* zero-result fallback tests
* typo/synonym mapping tests
* personalization fallback tests

---

# 4. Recommendation and Feed Ranking

## Business purpose

Recommendation systems rank content, products, creators, ads, restaurants, jobs, music, or videos to maximize user and business value.

Typical products:

* Instagram Feed / Reels
* Netflix homepage
* Spotify Home
* LinkedIn Feed
* YouTube recommendations
* TikTok feed
* Uber Eats restaurant ranking
* Etsy recommendations

## Core entities

* user
* candidate item
* feature vector
* ranking model
* retrieval model
* score
* multi-task prediction
* calibration metric
* impression
* click
* dwell
* conversion
* hide/report/negative feedback
* experiment variant

## Critical business metrics

* engagement
* retention
* session length
* click-through rate
* conversion
* creator/seller exposure
* diversity
* freshness
* calibration
* normalized entropy / ranking quality
* latency
* serving cost
* model stability

## Common failure modes

* irrelevant recommendations
* model score drift
* stale features
* feature missingness
* cold-start failure
* over-personalization
* feedback loops
* unsafe or low-quality content promoted
* ranking latency regression
* model launch breaks a subset of surfaces
* multi-model fleet becomes hard to monitor
* model looks healthy by availability but unhealthy by prediction quality

## Testable invariants

* blocked content must not be recommended
* unavailable items must not be ranked
* score combination must be deterministic
* missing feature fallback must not crash
* cold-start users should receive safe defaults
* experiment assignment must be stable
* model response schema must be valid
* ranking service must degrade gracefully if a feature store is unavailable
* all ranking predictions must be logged with model version and request context

## Project implication

For recommendation-like code, generated tests should protect:

* candidate eligibility
* feature fallback
* model response parsing
* ranking score composition
* experiment assignment
* safety filters
* stable ordering under deterministic inputs

Do not accept tests that only assert “ranking result is not null.”

## Benchmark scenario ideas

* ranking score comparator tests
* feature missing fallback tests
* blocked item exclusion tests
* cold-start fallback tests
* model version metadata tests
* experiment bucket stability tests
* candidate eligibility tests

---

# 5. Ads and Monetization

## Business purpose

Ads systems match advertisers with users while balancing advertiser ROI, user relevance, platform revenue, privacy, and brand safety.

Typical products:

* Meta ads ranking
* Google Ads
* TikTok ads
* Etsy Ads
* LinkedIn Ads
* sponsored search
* marketplace promoted listings

## Core entities

* advertiser
* campaign
* ad creative
* bid
* budget
* pacing
* user
* impression
* click
* conversion
* attribution
* auction
* quality score
* brand safety rule
* privacy constraint

## Critical business metrics

* revenue
* advertiser ROI / ROAS
* conversion rate
* click-through rate
* cost per action
* budget utilization
* pacing accuracy
* auction efficiency
* ad relevance
* user experience
* brand safety
* policy violation rate

## Common failure modes

* overspending campaign budget
* underdelivery due to pacing bug
* attribution window miscalculation
* invalid ad eligibility
* privacy-restricted users included
* unsafe content adjacency
* conversion tracking duplication
* auction tie-breaker instability
* wrong bid normalization
* delayed feedback creates stale supervision
* model improves revenue but harms user trust

## Testable invariants

* campaign spend must never exceed allowed budget rules
* paused campaigns must not serve
* rejected ads must not serve
* user privacy restrictions must be enforced
* attribution events must be deduplicated
* currency and timezone handling must be correct
* auction ranking must be deterministic under fixed inputs
* pacing should not allocate more than remaining budget
* brand-safety exclusions must be applied before ranking

## Project implication

Ads tests are valuable when they target money, eligibility, privacy, and pacing.

Generated tests should focus on:

* budget bounds
* eligibility filtering
* attribution deduplication
* auction ranking
* privacy exclusion
* currency/timezone edge cases

## Benchmark scenario ideas

* campaign budget cap tests
* paused campaign exclusion tests
* conversion deduplication tests
* auction tie-breaker tests
* timezone boundary tests
* privacy opt-out exclusion tests

---

# 6. E-Commerce and Marketplace

## Business purpose

E-commerce and marketplace systems connect buyers and sellers through search, catalog, cart, checkout, pricing, inventory, fulfillment, reviews, and dispute workflows.

Typical products:

* Amazon
* Shopify merchants
* Etsy
* eBay
* Uber Eats
* DoorDash marketplace
* app stores
* travel marketplaces
* creator marketplaces

## Core entities

* buyer
* seller
* listing / product
* SKU
* inventory
* cart
* order
* payment
* shipment / delivery
* refund
* review
* dispute
* promotion
* coupon
* tax
* fee

## Critical business metrics

* search-to-cart conversion
* checkout conversion
* gross merchandise value
* order completion rate
* refund rate
* seller success
* fulfillment speed
* cancellation rate
* cart abandonment
* fraud loss
* dispute rate
* page performance
* marketplace liquidity

## Common failure modes

* overselling inventory
* duplicate order creation
* coupon applied incorrectly
* cart price differs from checkout price
* tax/fee calculation mismatch
* item becomes unavailable during checkout
* order state machine allows invalid transition
* refund exceeds captured amount
* seller-restricted item shown to buyer
* search ranking harms seller fairness
* performance regression reduces conversion

## Testable invariants

* inventory must not go below zero
* checkout price must equal item + tax + fees - discounts
* an order must not be paid twice
* refund amount must not exceed captured amount
* cancelled orders must not ship
* shipped orders must not be cancelled without return workflow
* coupon usage limits must be enforced
* cart updates must be idempotent
* unavailable items must not be purchased
* seller policy restrictions must apply before checkout

## Project implication

E-commerce tests should target state transitions and money correctness.

Generated tests should be scored higher if they protect:

* inventory consistency
* pricing correctness
* order lifecycle
* refund/dispute boundaries
* idempotency
* promotion/coupon constraints
* seller/buyer eligibility

## Benchmark scenario ideas

* inventory reservation/release tests
* coupon stacking tests
* checkout idempotency tests
* refund bound tests
* order state transition tests
* unavailable item checkout tests
* price recomputation tests

---

# 7. Logistics and Dispatch

## Business purpose

Logistics systems match supply and demand across time and space.

Typical products:

* Uber rides
* Lyft rides
* DoorDash delivery
* Instacart fulfillment
* warehouse picking
* routing platforms
* local delivery networks

## Core entities

* rider / consumer
* driver / courier / dasher
* merchant
* order
* route
* ETA
* pickup
* dropoff
* supply
* demand
* matching decision
* pricing/incentive
* region/cell

## Critical business metrics

* fulfillment rate
* ETA accuracy
* pickup time
* delivery time
* cancellation rate
* driver utilization
* driver earnings
* marketplace balance
* late delivery rate
* batching efficiency
* cost per delivery
* incentive efficiency

## Common failure modes

* bad driver/order match
* invalid route
* over-batching
* infeasible delivery assignment
* stale ETA
* supply-demand imbalance
* unfair driver utilization
* incentive overspend
* cancellation spike
* zero-downtime migration failure in tier-zero dispatch service

## Testable invariants

* unavailable drivers must not be assigned
* cancelled orders must not be dispatched
* route constraints must be respected
* batch size limits must be enforced
* ETA must be non-negative and within reasonable bounds
* driver capacity must not be exceeded
* region boundaries must not produce invalid matches
* fallback dispatch must work if optimizer fails
* solver timeout must produce safe feasible solution or fail closed

## Project implication

Logistics tests are valuable when they cover feasibility constraints, fallback behavior, and optimization boundaries.

Generated tests should not try to prove the optimizer is globally optimal unless the case is small and deterministic. They should test:

* constraint enforcement
* invalid input handling
* fallback path
* timeout behavior
* stable decision under fixed inputs
* state transition correctness

## Benchmark scenario ideas

* driver unavailable exclusion tests
* route feasibility tests
* batch limit tests
* optimizer timeout fallback tests
* ETA boundary tests
* cancellation-before-dispatch tests

---

# 8. Payments and Fintech

## Business purpose

Payment systems move money safely and reliably across customers, merchants, banks, card networks, wallets, currencies, and regulators.

Typical products:

* Stripe
* Checkout.com
* PayPal
* Adyen
* Square
* in-app payments
* marketplace payouts
* subscriptions
* virtual cards
* bank transfers

## Core entities

* customer
* merchant
* payment intent
* charge
* authorization
* capture
* refund
* payout
* dispute
* invoice
* subscription
* card
* wallet
* currency
* exchange rate
* risk decision
* idempotency key

## Critical business metrics

* payment acceptance rate
* authorization success
* fraud rate
* chargeback rate
* dispute win rate
* payment latency
* checkout conversion
* reconciliation accuracy
* settlement correctness
* compliance status
* uptime

## Common failure modes

* duplicate charge
* lost capture
* refund exceeds captured amount
* idempotency failure
* race condition on payment state
* currency precision bug
* timezone billing bug
* subscription double billing
* webhook replay creates duplicate effects
* dispute evidence mishandled
* risk engine false positive/negative
* external provider outage not handled

## Testable invariants

* same idempotency key must not create duplicate charge
* authorized payment can be captured only once unless partial capture is supported
* refund cannot exceed captured amount
* failed payment must not create fulfilled order
* webhook replay must be idempotent
* currency arithmetic must use integer minor units or safe decimal handling
* payout must be linked to settled funds
* subscription cancellation must stop future billing
* card/network failures must be retried according to policy
* provider outage must trigger fallback or safe failure

## Project implication

Payments are a high-value domain for generated-test evaluation because business invariants are sharp and failures are costly.

Generated tests should be scored higher if they test:

* idempotency
* state machine transitions
* retries
* webhooks
* external provider failure
* amount bounds
* currency precision
* authorization/capture/refund lifecycle

## Benchmark scenario ideas

* idempotent payment creation tests
* refund boundary tests
* webhook replay tests
* subscription renewal/cancellation tests
* currency rounding tests
* provider timeout fallback tests
* double-submit checkout tests

---

# 9. Subscriptions and Billing

## Business purpose

Subscription systems manage recurring revenue, entitlement, billing cycles, trials, upgrades, downgrades, renewals, cancellation, and invoices.

Typical products:

* Netflix subscription
* Spotify Premium
* SaaS billing
* cloud usage billing
* creator subscriptions
* premium social features
* usage-based pricing

## Core entities

* account
* plan
* subscription
* invoice
* billing cycle
* trial
* renewal
* cancellation
* entitlement
* usage event
* proration
* payment method
* tax
* coupon

## Critical business metrics

* recurring revenue
* churn
* renewal rate
* payment recovery
* trial conversion
* entitlement accuracy
* billing support contacts
* invoice accuracy

## Common failure modes

* user charged after cancellation
* entitlement not revoked after failed renewal
* trial converts too early or too late
* proration miscalculated
* usage metering double counts
* invoice timezone boundary bug
* coupon applies beyond allowed period
* plan downgrade leaves premium entitlement
* retry logic creates duplicate invoices

## Testable invariants

* cancelled subscription must not renew
* active paid subscription must grant entitlement
* failed payment should enter grace/retry state
* trial end date must be calculated correctly
* proration must never be negative unless credit policy allows it
* usage events must be idempotent
* invoice totals must match line items
* plan transitions must update entitlements atomically

## Project implication

Subscription tests should focus on time, state, money, and entitlement consistency.

Benchmark scenario ideas:

* trial-to-paid transition tests
* cancellation boundary tests
* entitlement revoke tests
* proration tests
* invoice total tests
* usage metering idempotency tests

---

# 10. Trust and Safety

## Business purpose

Trust and safety systems reduce abuse and maintain platform integrity.

Typical products:

* Discord moderation
* YouTube policy enforcement
* Facebook/Instagram integrity
* X/Twitter spam and misinformation controls
* marketplace abuse detection
* fraud/scam reporting
* child safety systems
* community moderation

## Core entities

* user
* content
* report
* policy
* violation category
* enforcement action
* appeal
* moderation queue
* risk score
* account reputation
* community/server/group
* transparency metric

## Critical business metrics

* abuse prevalence
* report volume
* enforcement precision
* enforcement recall
* false positive rate
* appeal overturn rate
* time to action
* spam rate
* harmful content exposure
* moderator load
* user trust
* advertiser brand safety

## Common failure modes

* harmful content not removed
* benign content removed
* appeals not processed correctly
* report deduplication failure
* policy category mismatch
* repeat offender not escalated
* enforcement action too weak or too strong
* moderation model drift
* transparency metric not comparable over time
* content policy changes break historical metrics

## Testable invariants

* repeated reports should be deduplicated
* severe violations should escalate
* banned users should not regain restricted capabilities without appeal
* appeals should not erase audit history
* policy version should be recorded with decisions
* enforcement action must match violation severity
* restricted content must not be recommended
* user reports must be traceable
* moderator override must be audited

## Project implication

Trust/safety tests are valuable when they test auditability, policy versioning, escalation, and false-positive boundaries.

Generated tests should not just check “report created.” They should check:

* policy classification
* enforcement state transition
* audit trail
* appeal workflow
* repeat-offender escalation
* content eligibility after enforcement

## Benchmark scenario ideas

* report deduplication tests
* policy version tests
* appeal state transition tests
* repeat offender escalation tests
* banned content exclusion tests
* moderator override audit tests

---

# 11. Identity, Account, and Access

## Business purpose

Identity systems determine who the user is, what they can access, and how risk is handled.

Typical products:

* login
* signup
* OAuth
* SSO
* passkeys
* MFA
* account recovery
* enterprise identity
* admin permissions
* agent access control

## Core entities

* user
* account
* identity provider
* session
* token
* device
* role
* permission
* organization
* tenant
* policy
* risk signal
* audit event

## Critical business metrics

* login success rate
* account takeover rate
* MFA completion rate
* recovery success rate
* unauthorized access incidents
* session validity
* enterprise compliance
* support volume

## Common failure modes

* privilege escalation
* stale session remains valid
* token not revoked
* MFA bypass
* account recovery hijack
* tenant isolation violation
* role change not propagated
* audit log missing
* service account over-permissioned
* AI agent access not governed

## Testable invariants

* revoked token must not authenticate
* role downgrade must remove permissions
* tenant A must never access tenant B data
* MFA-required user must not bypass MFA
* admin action must be audited
* password reset token must expire
* session refresh must respect account status
* service account permissions must be least privilege
* agent access must respect user intent and data sensitivity

## Project implication

Access-control tests are high-value because small bugs can become security incidents.

Generated tests should target:

* permission matrix
* tenant isolation
* token lifecycle
* session expiry
* audit logging
* role propagation
* explicit approval for agent actions

## Benchmark scenario ideas

* role downgrade tests
* token revocation tests
* tenant isolation tests
* expired reset token tests
* admin audit log tests
* agent access policy tests

---

# 12. Notifications and Messaging

## Business purpose

Notification systems deliver timely, relevant, and safe communication across push, email, SMS, in-app inbox, chat, and webhooks.

Typical products:

* app push notifications
* email campaigns
* order updates
* ride/delivery updates
* chat systems
* support messages
* webhook notifications
* social DMs

## Core entities

* sender
* recipient
* message
* channel
* template
* delivery attempt
* retry
* preference
* unsubscribe
* device token
* webhook endpoint
* rate limit

## Critical business metrics

* delivery rate
* open rate
* click-through rate
* unsubscribe rate
* spam complaint rate
* latency
* duplicate notification rate
* user engagement
* customer support reduction

## Common failure modes

* duplicate notification
* missing critical notification
* wrong recipient
* notification sent after unsubscribe
* stale template data
* retry storm
* webhook replay side effects
* preference not respected
* delayed delivery for critical event
* PII leaked in notification

## Testable invariants

* unsubscribed users must not receive marketing messages
* transactional messages must follow policy
* retries must be idempotent
* recipient must match event owner
* templates must handle missing optional data
* push token invalidation must be handled
* webhook signatures must be verified
* rate limits must prevent storms

## Project implication

Notification tests should target idempotency, preferences, privacy, and event ownership.

Benchmark scenario ideas:

* unsubscribe preference tests
* duplicate delivery prevention tests
* stale template fallback tests
* webhook signature tests
* retry idempotency tests
* wrong-recipient guard tests

---

# 13. Experimentation and Analytics

## Business purpose

Experimentation systems help teams validate whether product changes improve real user outcomes.

Typical products:

* Netflix experimentation platform
* Spotify Confidence
* LinkedIn Feed experiments
* A/B testing platforms
* feature flag systems
* interleaving systems
* LLM eval platforms

## Core entities

* experiment
* variant
* assignment
* exposure
* metric
* guardrail metric
* sample
* holdout
* ramp
* treatment effect
* statistical test
* feature flag
* rollout

## Critical business metrics

* metric lift
* guardrail degradation
* experiment velocity
* decision accuracy
* false positive rate
* false negative rate
* sample ratio mismatch
* exposure correctness
* rollout safety

## Common failure modes

* unstable assignment
* user assigned to multiple conflicting variants
* exposure logged incorrectly
* metric leakage
* sample ratio mismatch
* peeking bias
* guardrail metric ignored
* experiment starts before instrumentation is ready
* offline eval passes but online experiment fails
* LLM eval confused with user validation

## Testable invariants

* same user must get stable assignment
* excluded users must not be assigned
* exposure should be logged once per rule
* mutually exclusive experiments must not overlap
* guardrail metrics must be present
* experiment config changes must be audited
* rollout percentage must be respected
* variant IDs must be valid
* offline eval result must not be treated as online validation

## Project implication

Experimentation knowledge maps directly to this project.

Your project’s benchmark and QualityGate should behave like an eval funnel:

```text
eval filters discard weak candidates before expensive real experiments or human review
```

Generated tests should validate:

* stable assignment
* metric logging
* guardrail presence
* rollout constraints
* config validation
* experiment result reproducibility

## Benchmark scenario ideas

* deterministic assignment tests
* sample ratio config tests
* exposure deduplication tests
* mutually exclusive experiment tests
* rollout percentage tests
* guardrail metric required tests

---

# 14. Reliability and Release Engineering

## Business purpose

Reliability systems protect users from bad deployments, outages, dependency failures, and overload.

Typical practices:

* SLOs
* error budgets
* canary deployment
* blue/green deployment
* automatic rollback
* health checks
* load shedding
* circuit breakers
* pre-production testing
* production readiness review
* incident postmortems

## Core entities

* service
* deployment
* release
* canary
* baseline
* metric
* alarm
* rollback
* dependency
* SLO
* SLI
* error budget
* incident
* runbook

## Critical business metrics

* availability
* latency
* error rate
* saturation
* time to detect
* time to mitigate
* time to recover
* customer impact
* rollback rate
* change failure rate
* incident frequency

## Common failure modes

* bad deployment not rolled back
* health check too shallow
* dependency outage not handled
* canary analysis misses small subset failure
* rollback unsafe
* alert too noisy
* alert missing for critical journey
* service overload
* capacity miscalculation
* stale fallback
* incident lessons not converted into tests

## Testable invariants

* failed health check must remove instance from rotation
* dependency timeout must not hang request forever
* circuit breaker must open under repeated failure
* retry policy must not amplify overload
* rollback must restore previous known-good version
* canary must compare baseline and candidate metrics
* critical user journey must have SLI coverage
* incident action items should create regression tests

## Project implication

Your project should borrow reliability thinking:

```text
generated test candidate = canary
QualityGate = automated canary analysis
audit_bench.py = report reproducibility
failure ledger = postmortem memory
run_kind = deployment environment metadata
```

Benchmark scenario ideas:

* retry/circuit breaker tests
* health check tests
* fallback path tests
* timeout boundary tests
* rollback state tests
* canary metric comparison tests

---

# 15. Data Platform and Reporting

## Business purpose

Data platforms provide trusted datasets, metrics, dashboards, logs, analytics, and decision support.

Typical products:

* Netflix analytics
* LinkedIn data platform
* DoorDash data platform
* Cloudflare analytics/reporting
* event pipelines
* BI dashboards
* product metrics
* ML training data

## Core entities

* event
* schema
* dataset
* pipeline
* job
* partition
* dashboard
* metric
* lineage
* data owner
* quality check
* retention policy

## Critical business metrics

* data freshness
* data completeness
* data correctness
* pipeline success rate
* query latency
* schema compatibility
* lineage coverage
* dashboard trust
* metric reproducibility

## Common failure modes

* duplicate events
* missing events
* schema drift
* late data
* broken dashboard
* metric definition changes silently
* report number cannot be reproduced
* data retention violates policy
* raw and derived metrics disagree
* fake/smoke data enters production metrics

## Testable invariants

* event schema must validate
* metric calculation must be deterministic
* derived totals must reconcile with raw data
* late data handling must be explicit
* duplicate events must be deduplicated
* report numbers must be reproducible
* schema version must be recorded
* data source must be traceable
* smoke/fake data must be excluded from business metrics

## Project implication

This is directly related to your benchmark contamination issue.

Your platform must enforce:

* raw artifact preservation
* schema versioning
* report-number reproduction
* fake/real separation
* metric lineage
* run metadata

Benchmark scenario ideas:

* report recomputation tests
* schema drift tests
* duplicate event tests
* fake data exclusion tests
* raw-to-summary reconciliation tests
* metric denominator tests

---

# 16. AI/ML Platform and Model Governance

## Business purpose

AI/ML platforms support model training, deployment, monitoring, registry, evaluation, governance, and responsible AI.

Typical systems:

* model registry
* feature store
* offline evaluation
* online serving
* model cards
* experiment tracking
* model monitoring
* drift detection
* human approval workflow
* responsible AI review

## Core entities

* model
* model version
* feature
* dataset
* training run
* evaluation run
* deployment
* prediction
* label
* drift metric
* owner
* approval
* model card

## Critical business metrics

* model quality
* calibration
* latency
* cost
* drift
* stability
* training efficiency
* rollback frequency
* compliance approval
* ownership coverage

## Common failure modes

* model version not tracked
* stale features
* training/serving skew
* offline metric improves but online metric worsens
* model drift not detected
* owner unknown
* missing approval
* biased or unsafe prediction
* expensive model with weak business lift
* model fleet too large to operate reliably

## Testable invariants

* every prediction should include model version
* model must have an owner
* model deployment must have evaluation metadata
* feature schema must match training expectation
* fallback model must exist for critical path
* model output schema must validate
* offline evaluation must not be confused with production validation
* high-risk models must have governance checks

## Project implication

Your project should treat generated tests like model candidates:

```text
candidate -> evaluation -> ledger -> report -> human review
```

Required metadata:

* model name
* prompt version
* run_kind
* source repo
* commit SHA
* input manifest
* artifact path
* QualityGate verdict
* human-review status

Benchmark scenario ideas:

* model version metadata tests
* evaluation record schema tests
* fallback model tests
* drift metric schema tests
* owner-required tests

---

# 17. Developer Productivity and Coding Agents

## Business purpose

Developer productivity systems reduce engineering bottlenecks across coding, review, documentation, testing, deployment, and security.

Typical systems:

* GitHub Copilot coding agent
* Copilot code review
* Claude Code
* Codex
* PRD review agent
* test generation agent
* code search agent
* CI failure diagnosis agent

## Core entities

* task
* repository
* branch
* diff
* review
* test result
* instruction file
* agent run
* artifact
* permission
* approval

## Critical business metrics

* cycle time
* review time
* defect escape rate
* test pass rate
* merge confidence
* code review coverage
* security finding rate
* developer satisfaction
* agent cost
* rollback rate

## Common failure modes

* agent changes unrelated files
* agent claims success without running tests
* agent ignores repo instructions
* agent exposes secrets
* agent runs expensive real models
* agent generates fake-green tests
* reviewer agent edits code
* builder and reviewer collide in same worktree
* generated code passes tests but violates business invariant
* deterministic tools are not used alongside LLM review

## Testable invariants

* agent must list changed files
* success claims require command evidence
* reviewer mode must not edit files
* push requires human approval
* `.env` must not be read or printed
* real model calls require explicit approval
* test suite must run after code changes
* generated tests must be judged, not accepted blindly

## Project implication

This domain is the core of your platform’s engineering process.

Your project should use:

* `CLAUDE.md`
* `AGENTS.md`
* `docs/TASKS.md`
* `docs/HANDOFF.md`
* `docs/RUN_POLICY.md`
* `tests/conftest.py`
* `scripts/audit_bench.py`
* reviewer-agent workflow

Benchmark scenario ideas:

* agent diff review checklist
* fake-green test candidate cases
* report-number reproduction tasks
* forbidden-action guard tests
* generated-test QualityGate tasks

---

# 18. Security, Privacy, and Compliance

## Business purpose

Security and compliance systems protect users, data, infrastructure, payments, and regulated workflows.

Typical systems:

* secrets management
* IAM
* data classification
* audit logs
* privacy controls
* PCI compliance
* SOC2 controls
* EU AI Act / AI governance
* AI agent access governance
* threat detection

## Core entities

* secret
* credential
* permission
* policy
* data classification
* user consent
* audit log
* compliance control
* risk score
* incident
* data subject
* AI agent identity

## Critical business metrics

* unauthorized access incidents
* secrets exposure
* policy violation rate
* audit coverage
* compliance pass rate
* data deletion success
* privacy request SLA
* vulnerability remediation time
* privileged command approval rate

## Common failure modes

* secret committed to repo
* over-permissioned role
* policy change breaks critical flow
* data access not audited
* PII leaked into logs
* user deletion incomplete
* privacy opt-out ignored
* AI agent accesses sensitive data without approval
* compliance evidence missing
* privileged command has no approval trail

## Testable invariants

* secrets must not be printed
* PII must not appear in logs
* deletion requests must remove or anonymize relevant data
* consent must gate data use
* access policy changes must be auditable
* privileged actions require approval
* data export must be scoped to user
* agent access must respect data sensitivity

## Project implication

Your project already needs security rules:

* do not read `.env`
* do not print secrets
* do not run real model calls without approval
* do not send proprietary code to external systems without policy
* do not mix fake and real data
* preserve audit evidence

Benchmark scenario ideas:

* secret redaction tests
* IAM policy simulation tests
* audit log required tests
* consent gate tests
* PII logging tests
* AI-agent permission tests

---

# 19. Domain-to-Test Pattern Matrix

| Domain           | Most valuable test pattern                                          |
| ---------------- | ------------------------------------------------------------------- |
| Search           | eligibility, filters, ranking stability, zero-result fallback       |
| Recommendation   | candidate filtering, feature fallback, model metadata               |
| Ads              | budget cap, eligibility, attribution dedupe, privacy exclusion      |
| E-commerce       | inventory, order state, checkout idempotency, refund bounds         |
| Logistics        | matching constraints, route feasibility, fallback dispatch          |
| Payments         | idempotency, authorization/capture/refund lifecycle, webhook replay |
| Subscription     | renewal/cancellation, entitlement, proration, usage metering        |
| Trust & Safety   | report dedupe, enforcement state, appeal workflow, audit trail      |
| Identity         | token lifecycle, role propagation, tenant isolation, MFA            |
| Notifications    | recipient correctness, preference respect, retry idempotency        |
| Experimentation  | stable assignment, exposure logging, guardrail metrics              |
| Reliability      | timeout, retry, circuit breaker, healthcheck, rollback              |
| Data Platform    | schema validation, metric recomputation, fake-data exclusion        |
| AI/ML Platform   | model versioning, evaluation record, fallback, owner metadata       |
| Dev Productivity | diff scope, command evidence, reviewer non-editing mode             |
| Security/Privacy | secret redaction, audit log, consent, permission boundaries         |

---

# 20. How This Knowledge Should Affect This Project

## 20.1 QualityGate should reward business invariants

Generated tests should receive stronger review signals if they cover:

* money correctness
* state machine correctness
* idempotency
* access control
* audit trail
* eligibility filtering
* metric calculation
* fake-data exclusion
* fallback behavior
* external provider failure
* time/currency boundary
* duplicate-event handling

Generated tests should receive weaker signals if they only cover:

* constructors
* getters/setters
* non-null results
* trivial happy paths
* duplicated existing tests
* placeholder tests
* implementation details without behavior

---

## 20.2 Benchmark samples should include business-pattern tags

Future benchmark manifest should include:

```json
{
  "business_domain": "payments|search|ads|marketplace|data_platform|identity|reliability|other",
  "business_pattern": "idempotency|state_transition|eligibility|ranking|metric_recompute|fallback|audit_trail",
  "risk_level": "low|medium|high",
  "expected_business_invariant": "string"
}
```

This allows reports to answer:

```text
What kind of business risk did the generated test protect?
```

Not just:

```text
Did the generated test pass?
```

---

## 20.3 Failure ledger should classify business failures

Future `FAILURE_LEDGER.md` entries should include:

```text
failure_type:
- fake_green
- metric_contamination
- idempotency_gap
- state_transition_gap
- missing_business_oracle
- data_lineage_gap
- permission_gap
- fallback_gap
- external_dependency_gap
```

---

## 20.4 Agent prompts should ask for business invariants

When asking an agent to generate or review tests, include:

```text
Identify the business invariant being protected.
If no meaningful business invariant is protected, classify the test as weak or fake-green risk.
```

Review output should include:

```text
business_invariant:
risk_covered:
oracle_strength:
fake_green_risk:
human_review_note:
```

---

# 21. Immediate Backlog Derived from This Knowledge

## Immediate

1. Add business-domain tags to benchmark design.
2. Update `docs/QUALITY_GATE.md` to define business-invariant value.
3. Add generated-test review rubric:

   * What invariant is protected?
   * Is the oracle meaningful?
   * Is this just fake-green?
4. Add examples of high-value vs low-value tests.
5. Extend `scripts/audit_bench.py` later to group results by business pattern after metadata exists.

## Next

1. Add `docs/quality/BUSINESS_INVARIANT_RUBRIC.md`.
2. Add benchmark cases for:

   * payment idempotency
   * order state transition
   * search filter eligibility
   * experiment assignment stability
   * fake-data exclusion from metrics
3. Add failure ledger categories for business-value gaps.

## Later

1. Add business-domain-aware candidate scoring.
2. Add mutation/fault-based evidence for business-critical paths.
3. Add real-bug fail-to-pass benchmark cases tagged by domain.
4. Add agent skill:

   * `business-invariant-test-review`

---

# 22. First Candidate Business Benchmark Cases

These are not external datasets. They are scenario patterns that can be implemented as small Java samples or selected from open-source projects.

## Case 1: Payment idempotency

Invariant:

```text
Retrying the same payment request with the same idempotency key must not create a duplicate charge.
```

Why valuable:

High business risk, easy to test, strong oracle.

## Case 2: Refund bound

Invariant:

```text
Total refunded amount must not exceed captured amount.
```

Why valuable:

Money correctness and state transition.

## Case 3: Order cancellation state

Invariant:

```text
A shipped order cannot be cancelled through the normal cancellation path.
```

Why valuable:

Common e-commerce lifecycle boundary.

## Case 4: Inventory reservation

Invariant:

```text
Inventory must not go negative under reservation and release operations.
```

Why valuable:

Marketplace correctness.

## Case 5: Search eligibility

Invariant:

```text
Restricted or unavailable items must not appear in search results.
```

Why valuable:

Search correctness and compliance.

## Case 6: Experiment assignment

Invariant:

```text
The same user must receive the same experiment variant under stable experiment configuration.
```

Why valuable:

Experiment validity.

## Case 7: Notification preference

Invariant:

```text
A user who unsubscribed from marketing notifications must not receive marketing messages.
```

Why valuable:

User trust and compliance.

## Case 8: Webhook replay

Invariant:

```text
Replaying the same webhook event must not duplicate side effects.
```

Why valuable:

Common external integration risk.

## Case 9: Role downgrade

Invariant:

```text
After a role downgrade, restricted permissions must be removed immediately.
```

Why valuable:

Security and access control.

## Case 10: Report metric denominator

Invariant:

```text
Fake/dryrun/smoke rows must not enter real headline metrics.
```

Why valuable:

Directly tied to this project’s historical contamination issue.

---

# 23. Final Operating Principle

For this project, business knowledge should be used as a filter:

```text
Does this generated test protect a meaningful business invariant?
```

If the answer is no, the test should not be considered strong even if it passes.

The strongest generated tests usually cover one of:

```text
money
identity
permission
state transition
ranking eligibility
experiment validity
data lineage
audit trail
external dependency failure
fallback behavior
compliance boundary
```

The project should remain focused:

```text
AI-generated test candidate evaluation / audit / engineering-usability platform
```

Do not broaden into a generic internet business platform.
Use this knowledge to improve test quality, benchmark design, and agent review.
