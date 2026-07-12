# ADR-0006: Cache-Affinity Route Policy

- **Status:** Accepted
- **Date:** 2026-07-12
- **Decision version:** 1.2.0
- **Decision owners:** AuraGateway project maintainers
- **Applies from:** Phase 4
- **Supersedes:** None

## Context

AuraGateway must preserve trajectory value without pretending it can observe provider cache residency directly. A per-turn router can discard reusable context by changing provider or model during a session. At the same time, blindly preserving a route can violate capability, safety, quality, or failure-handling requirements.

The first Gate 5 implementation boundary established deterministic, privacy-safe session-route state. The second boundary added deterministic authorization for explicit warm-affinity, TTL, provider-failure, capability, safety, quality, reset, and benchmark-control transitions.

A third regulation boundary is required because individually valid decisions can still create unsafe trajectories. Repeated route changes can create route thrash. Repeated provider attempts can exceed retry budgets, repeat the same failed recovery, or duplicate an ambiguous generation whose completion state is unknown.

## Decision

AuraGateway will separate routing into three deterministic layers:

```text
session-route state
    ↓
single-transition policy authorization
    ↓
trajectory regulation
```

The trajectory-regulation layer consumes only typed, metadata-safe history. It does not inspect raw prompts, user messages, retrieved documents, model output, or raw provider payloads.

### Session-route state

The state records only:

- a SHA-256 session identity hash;
- the active provider and model alias;
- the last trustworthy cache-evidence timestamp, when one exists;
- one cache-affinity status;
- a monotonic route-change count;
- one allowed route reason.

Allowed cache-affinity states:

```text
cold
plausibly_warm
expired
unknown
```

Allowed route reasons:

```text
session_start
warm_cache_affinity
ttl_expired
provider_failure
capability_requirement
safety_requirement
quality_guardrail
session_reset
benchmark_control
```

No additional reason may be added without versioning this ADR and updating fixtures and tests.

### Single-transition policy

The single-transition policy authorizes or blocks an explicit caller-proposed target. It does not autonomously select a provider or model.

It enforces:

- warm-route preservation only inside the configured TTL;
- TTL expiry without a hidden provider/model switch;
- provider-failure rerouting only after a definite failure;
- no provider-failure reroute after an ambiguous response;
- capability, safety, and quality reroutes only when the named active-route gate failed;
- fully eligible reroute targets;
- no inherited cache evidence on a new route.

### Route-history regulation

Applied route decisions are retained as an ordered chain containing:

- the authorized policy decision;
- the resulting typed state transition;
- a contiguous sequence index;
- a timezone-aware application timestamp.

The history must be contiguous, belong to one hashed session, and reconcile with the session state’s route-change count.

The default trajectory regulation permits one provider/model binding change per session. A second non-exempt binding change is blocked as `BLOCKED_ROUTE_THRASH`.

The following transitions are exempt from the route-thrash limit:

```text
session_reset
benchmark_control
```

The exemption exists because a reset terminates the route and an explicit benchmark transition is a controlled experimental action. It does not create a production routing exemption.

### Retry regulation

Provider retries are separate from rerouting.

A retry is authorized only when:

- the previous attempt ended in a definite failure;
- the provider classified the failure as retryable;
- the configured retry budget is not exhausted;
- the logical request fingerprint is unchanged;
- the provider/model route is unchanged;
- the recovery-action fingerprint has not already been used in the chain.

The default maximum is one retry. The contract allows at most three only for deterministic policy fixtures and future versioned policies.

An ambiguous response is always non-retryable inside this boundary because another generation could duplicate an already completed but unobserved response.

A provider/model change is never represented as a retry. It must pass through the route-policy boundary.

Repeating an already-used recovery-action fingerprint is blocked as `BLOCKED_INVALID_RETRY`. This is the bounded stagnation control for Gate 5; it does not claim universal agent-loop detection.

## Structural invariants

- Provider and model are present or absent together.
- `unavailable` is never an executable active provider.
- Session identity is represented only by a lowercase SHA-256 digest.
- New sessions are cold and contain no fabricated cache evidence.
- Plausibly warm and expired states require an active route and an evidence timestamp.
- `warm_cache_affinity` cannot change provider or model.
- `ttl_expired` requires an expired state.
- `session_reset` clears the route and cache evidence.
- Route-change count increments exactly once when provider/model binding changes.
- Every transition result carries the reason that appears on the resulting state.
- Applied route history contains authorized policy decisions only.
- Route-history sequence and state chaining are contiguous.
- Route-history change counts reconcile with the current session state.
- A second non-exempt route change is blocked by the default policy.
- Ambiguous provider outcomes never authorize retries.
- Retry chains remain on one logical request and one provider/model route.
- Retry budgets are explicit and bounded.
- Reused recovery actions are blocked.
- Blocked regulation decisions never expose executable transitions or retry attempts.

## Consequences

### Positive

- Gate 5 behavior is split into inspectable state, authorization, and regulation boundaries.
- Route changes are queryable and countable across the trajectory.
- Repeated switching fails closed before another transition is applied.
- Ambiguous provider responses cannot trigger blind duplicate generation.
- Retry budget and recovery novelty are machine-enforced.
- Raw session, prompt, provider-payload, and output content remain outside evidence artifacts.
- Deterministic fixtures can reproduce policy and regulation evidence without provider calls.

### Negative

- The default one-change limit is intentionally conservative and may escalate trajectories that could theoretically recover through another route.
- Recovery novelty is represented by fingerprints, not semantic proof that a recovery action is genuinely useful.
- The policy still does not rank candidate routes or calculate expected trajectory cost.
- Full loop, stagnation, and budget regulation beyond provider retries remains later agent-harness work.

## Required verification

Implementation must prove that:

- valid cold, plausibly warm, expired, unknown, and reset states validate;
- provider/model partial bindings fail;
- warm or expired states without evidence fail;
- unknown reason strings fail;
- warm-affinity transitions preserve the active route;
- explicit binding changes increment the route-change count once;
- reset clears binding and evidence;
- capability, safety, and quality failures require eligible targets;
- ambiguous provider responses block rerouting and retries;
- the first permitted route change is authorized;
- a second non-exempt route change is detected and blocked;
- benchmark-control and reset exemptions remain explicit;
- one bounded retry after a definite retryable failure is authorized;
- non-retryable failures are blocked;
- retry-budget exhaustion is blocked;
- request-fingerprint and route changes are not disguised as retries;
- repeated recovery-action fingerprints are blocked;
- fixture, report, and manifest hashes reproduce;
- contracts reject extra fields and are frozen;
- no provider call is required.

## Claim boundary

Gate 5 proves deterministic session-route state, explicit transition authorization, route-history regulation, route-thrash blocking under the named default, bounded retry authorization, and ambiguous-response duplicate protection in fixed local fixtures.

It does not prove provider cache residency, exact provider TTL, autonomous route selection, optimal trajectory cost, universal loop detection, task-quality non-inferiority, latency reduction, cost reduction, measured A/B/C results, deployment safety, or production readiness.
