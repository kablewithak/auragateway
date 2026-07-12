# ADR-0006: Cache-Affinity Route Policy

- **Status:** Accepted
- **Date:** 2026-07-12
- **Decision owners:** AuraGateway project maintainers
- **Applies from:** Phase 4
- **Supersedes:** None

## Context

AuraGateway must preserve trajectory value without pretending it can observe provider cache residency directly. A per-turn router can discard reusable context by changing provider or model during a session. At the same time, blindly preserving a route can violate capability, safety, quality, or failure-handling requirements.

The first Gate 5 implementation boundary therefore needs a deterministic, privacy-safe session-route state before it needs a cost optimizer or autonomous route selector.

## Decision

AuraGateway will represent session routing through frozen Pydantic v2 contracts and pure state-transition functions.

The state records only:

- a SHA-256 session identity hash;
- the active provider and model alias;
- the last trustworthy cache-evidence timestamp, when one exists;
- one cache-affinity status;
- a monotonic route-change count;
- one allowed route reason.

The allowed cache-affinity states are:

```text
cold
plausibly_warm
expired
unknown
```

The allowed route reasons are:

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

The state-transition layer does not choose a route. It applies an already-authorized target state and proves structural invariants. The later policy engine remains responsible for deciding whether a requested transition is permitted.

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

## Consequences

### Positive

- Gate 5 policy can be built on deterministic state instead of dictionaries.
- Route changes become inspectable and countable.
- Raw session, user, prompt, and provider payload content remain outside the boundary.
- TTL, failure, capability, safety, and quality logic can evolve behind a stable contract.
- Negative controls can reject invalid states before provider execution.

### Negative

- The first slice does not yet decide route eligibility or expected trajectory cost.
- Cache warmth remains a bounded policy state, not proof of provider residency.
- Additional typed fixtures and transition tests are required as policy behavior is added.

## Required verification

Implementation must prove that:

- valid cold, plausibly warm, expired, unknown, and reset states validate;
- provider/model partial bindings fail;
- warm or expired states without evidence fail;
- unknown reason strings fail;
- warm-affinity transitions preserve the active route;
- explicit binding changes increment the route-change count once;
- reset clears binding and evidence;
- contracts reject extra fields and are frozen;
- no provider call is required.

## Claim boundary

This ADR and its first implementation slice prove only the deterministic session-route state boundary. They do not prove route-policy safety, cache residency, provider TTL, route-thrash prevention across complete trajectories, quality non-inferiority, latency reduction, cost reduction, or benchmark readiness.
