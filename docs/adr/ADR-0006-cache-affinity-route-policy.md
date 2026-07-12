# ADR-0006: Cache-Affinity Route Policy

- **Status:** Accepted
- **Date:** 2026-07-12
- **Decision version:** 1.1.0
- **Decision owners:** AuraGateway project maintainers
- **Applies from:** Phase 4
- **Supersedes:** ADR-0006 decision version 1.0.0

## Context

AuraGateway must preserve trajectory value without pretending it can observe provider cache residency directly. A per-turn router can discard reusable context by changing provider or model during a session. Blindly preserving a route can also violate capability, safety, quality, or provider-failure requirements.

The first Gate 5 slice established a deterministic, privacy-safe session-route state and a pure transition layer. That layer deliberately applies an already-authorized target state and does not decide whether a transition is safe.

The next boundary must authorize or block proposed transitions without becoming an autonomous model selector, pricing optimizer, or provider executor.

## Decision

AuraGateway will separate route policy into two layers:

1. **Policy authorization** evaluates an explicit proposed transition and returns a typed `authorized` or `blocked` decision.
2. **State transition** applies only an authorized transition through the existing pure state-transition function.

The policy layer does not choose a provider or model. A caller must supply:

- the current route state;
- one explicit proposed transition;
- active-route capability, safety, and quality eligibility;
- target-route capability, safety, and quality eligibility when a target route exists;
- a timezone-aware evaluation time;
- a bounded warm-affinity TTL;
- provider response certainty and a typed provider error code where relevant.

### Provider response certainty

```text
none
definite_failure
ambiguous
```

An ambiguous provider response blocks a provider-failure reroute because blind duplicate generation could repeat an uncertain external action.

### Policy results

```text
authorized
blocked
```

Every result includes:

- policy ID and version;
- evaluation time;
- the proposed route reason;
- a bounded decision code;
- the authorized transition only when authorization succeeds.

Blocked results never carry an executable transition.

## Authorization rules

### Warm cache affinity

Authorize preservation only when:

- provider/model binding is unchanged;
- active route remains capability-, safety-, and quality-eligible;
- cache evidence time is present and not in the future;
- elapsed time is less than or equal to the configured TTL.

The state is `plausibly_warm`. This is policy evidence, not proof of provider cache residency.

### TTL expiry

Authorize TTL expiry only when:

- elapsed time is greater than the configured TTL;
- provider/model binding is unchanged;
- the proposed state is `expired`.

TTL expiry marks the current route eligible for later re-evaluation. It does not itself select or activate a replacement route.

### Provider failure

Authorize reroute only when:

- response state is `definite_failure`;
- a typed provider error code exists;
- provider/model binding changes;
- target route satisfies all capability, safety, and quality gates;
- the new route begins with `unknown` cache affinity and no inherited cache evidence.

An `ambiguous` response is blocked.

### Capability, safety, and quality requirements

Authorize reroute only when the named active-route gate has failed and the target route satisfies all hard eligibility gates.

A still-eligible active route cannot be switched under a fabricated capability, safety, or quality reason.

### Session reset

Authorize a structurally valid reset that clears route binding and cache evidence.

### Benchmark control

Authorize an explicit eligible route change needed by the frozen benchmark design. This is not a general manual override and remains subject to benchmark constitution and namespace-isolation controls.

## Structural invariants

The state layer continues to enforce:

- provider and model are present or absent together;
- `unavailable` is never an executable active provider;
- session identity is represented only by lowercase SHA-256;
- new sessions are cold and contain no fabricated cache evidence;
- plausibly warm and expired states require an active route and evidence timestamp;
- route-change count increments exactly once when provider/model binding changes.

The policy layer additionally enforces:

- active eligibility identity matches the active route;
- target eligibility identity matches the proposed target route;
- bound targets require target eligibility;
- unbound targets do not carry target eligibility;
- failure states require a typed provider error code;
- provider error codes cannot appear without a failure state;
- future cache evidence is rejected;
- blocked decisions cannot contain executable transitions;
- authorized decision codes match their route reasons.

## Decision priority

The engine evaluates one explicit proposed reason rather than selecting among competing interventions. This prevents hidden routing priorities.

For `provider_failure`, ambiguous response state blocks before any reroute authorization. For every reroute reason, target eligibility and cache-state reset requirements are evaluated before authorization.

## Consequences

### Positive

- Policy and state mutation remain independently testable.
- Warm affinity cannot silently defeat hard capability, safety, or quality gates.
- TTL semantics are explicit and deterministic.
- Ambiguous provider responses cannot trigger blind duplicate generation.
- Ineligible targets fail closed.
- Decision evidence is machine-readable without raw prompts, sessions, outputs, or provider payloads.
- Future cost-aware candidate selection can sit before this authorization seam without changing state contracts.

### Negative

- The caller must construct an explicit candidate transition and eligibility snapshots.
- This slice does not rank eligible routes by cost.
- Route-thrash detection still requires trajectory history beyond one transition.
- Retry budgets and stagnation regulation remain separate work.
- TTL remains a configured benchmark assumption, not a discovered provider guarantee.

## Required verification

Implementation must prove that:

- eligible warm routes are preserved within TTL;
- warm preservation is blocked beyond TTL;
- TTL expiry is authorized only after TTL and without changing binding;
- definite provider failure can authorize an eligible reroute;
- ambiguous provider response blocks provider-failure reroute;
- capability, safety, and quality reroutes require the named active-route failure;
- target routes must satisfy all hard eligibility gates;
- rerouted routes do not inherit cache evidence;
- session reset remains authorized and structurally safe;
- policy contracts are frozen and reject extra fields;
- TTL and active-capability metamorphic boundaries behave deterministically;
- no provider call is required.

## Experiment impact

```text
runtime_condition=none
active_causal_contrast=none
measured_execution=prohibited
controlled_route_policy_asset=implemented but not frozen for Gate 9
frozen retrieval, episodes, prefix, and Gate 4 telemetry assets=unchanged
```

## Claim boundary

Decision version 1.1.0 proves deterministic authorization for explicit warm-affinity, TTL, provider-failure, capability, safety, quality, reset, and benchmark-control transitions.

It does not prove provider cache residency, exact provider TTL, autonomous route selection, cheapest trajectory cost, route-thrash prevention across complete trajectories, retry safety, task-quality non-inferiority, latency reduction, cost reduction, or benchmark readiness.
