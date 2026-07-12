# AuraGateway Gate 5 Route-Policy Decision Boundary

## Status

```text
phase=Phase 4 — Cache-Affinity Controller and Trajectory Regulation
gate=Gate 5 — Route Policy
slice=2 — deterministic policy authorization
policy_id=gate5-route-policy-v1
policy_version=1.0.0
provider_calls=none
A/B/C execution=not started
```

## Purpose

This slice decides whether one explicit route-state transition is permitted. It does not choose a model, call a provider, calculate current pricing, or execute a benchmark condition.

The architecture is:

```text
explicit proposed transition
  + active-route eligibility
  + target-route eligibility
  + TTL and evaluation time
  + provider response certainty
  ↓
route-policy authorization
  ↓
authorized transition OR typed block
  ↓
existing pure route-state transition
```

## Inputs

`RoutePolicyEvaluationRequest` contains only metadata-safe values:

```text
policy ID and version
bounded TTL seconds
timezone-aware evaluation time
existing typed route state and proposed transition
provider/model aliases
capability eligibility
safety eligibility
quality eligibility
provider response certainty
typed provider error code where relevant
```

It contains no raw session identifier, prompt, user message, retrieved document, model output, secret, or raw provider payload.

## Authorization matrix

| Proposed reason | Required evidence | Authorized outcome |
|---|---|---|
| `warm_cache_affinity` | Same binding, fully eligible active route, evidence age within TTL | Preserve active route as `plausibly_warm` |
| `ttl_expired` | Same binding, evidence age beyond TTL | Mark active route `expired` for later re-evaluation |
| `provider_failure` | Definite failure, typed error, eligible different target | Reroute with target cache state `unknown` |
| `capability_requirement` | Active capability gate failed, fully eligible target | Reroute |
| `safety_requirement` | Active safety gate failed, fully eligible target | Reroute |
| `quality_guardrail` | Active quality gate failed, fully eligible target | Reroute |
| `session_reset` | Structurally valid cleared target | Reset |
| `benchmark_control` | Explicit different fully eligible target | Controlled reroute |

## Fail-closed decisions

The policy blocks:

```text
ambiguous provider response
warm preservation after TTL
TTL expiry before TTL
unconfirmed provider failure
fabricated capability/safety/quality reason
ineligible target route
route-changing transition that inherits cache evidence
reroute target that is not marked unknown
reason and state mismatch
```

## Deterministic fixtures

```text
data/provider_fixtures/routing/route_policy_cases.json
```

The fixture set includes:

```text
warm preservation authorized
warm preservation beyond TTL blocked
TTL expiry authorized
premature TTL expiry blocked
definite provider failure reroute authorized
ambiguous provider response blocked
capability reroute authorized
unneeded capability reroute blocked
```

Additional unit tests cover safety, quality, target ineligibility, reset, contract freezing, identity mismatch, future evidence, and decision-shape enforcement.

Metamorphic tests prove:

```text
changing only elapsed time from TTL to TTL+1 changes warm authorization
changing only active capability eligibility changes capability-reroute authorization
```

## Frozen-asset impact

This slice must not modify:

```text
benchmark constitution
corpus or retrieval assets
held-out or functional episodes
runtime episode selection
static-anchor registry
prefix fingerprints
Gate 4 telemetry fixtures or hashes
provider calibration fixtures
```

## Current permitted claim

> AuraGateway can deterministically authorize or block explicit route transitions using typed warm-affinity, TTL, provider-response, capability, safety, and quality evidence while preventing ambiguous-response reroutes and ineligible targets.

## Non-claims

```text
No proof of provider cache residency.
No exact provider TTL claim.
No autonomous route selection.
No current provider pricing or cost optimization.
No trajectory-level route-thrash proof.
No retry-budget or stagnation regulation proof.
No A/B/C benchmark result.
No quality non-inferiority result.
No latency or cost saving claim.
```

## Next Gate 5 boundary

The next slice should add trajectory regulation:

```text
route-decision history
route-thrash detection
bounded provider retry authorization
ambiguous-response duplicate protection across attempts
invalid-retry and stagnation controls
Gate 5 deterministic report and closeout evidence
```
