# AuraGateway Session Route State

## Purpose

This document defines the first deterministic Gate 5 boundary. It introduces session-route state, allowed route reasons, structural transitions, and invalid-state controls without implementing provider selection or measured A/B/C execution.

## Scope

Implemented:

```text
SessionRouteInitialization
SessionRouteState
SessionRouteTransitionRequest
SessionRouteTransitionResult
CacheAffinityStatus
RouteReason
RouteTransitionKind
initialize_session_route
apply_session_route_transition
```

Not implemented:

```text
capability calibration
expected trajectory-cost calculation
TTL duration selection
provider-failure retry policy
ambiguous-response regulation
route-thrash detector
quality guardrail integration
benchmark runner
```

## Privacy boundary

The contract accepts a lowercase SHA-256 `session_id_hash`. It rejects raw session identifiers through strict field definitions and `extra="forbid"`.

It does not contain:

```text
raw user content
raw prompt content
retrieved documents
provider payloads
credentials
PII
```

## State meanings

| State | Meaning | Evidence rule |
|---|---|---|
| `cold` | No reusable cache value is claimed | Cache timestamp must be absent |
| `plausibly_warm` | Current route may retain reusable context | Active route and timestamp required |
| `expired` | Prior evidence exists but the warm window is no longer trusted | Active route and timestamp required |
| `unknown` | Cache state cannot be classified safely | No cache-efficiency claim follows |

`plausibly_warm` is a policy state. It is not proof of provider cache residency.

## Transition boundary

`apply_session_route_transition` does not decide whether a route should change. It records a target state after another policy component has authorized the transition.

This separation prevents the state contract from becoming a hidden router and leaves a clean seam for the next Gate 5 slice.

## Deterministic fixture set

```text
data/provider_fixtures/routing/session_state_cases.json
```

The fixture set contains:

```text
4 valid state cases
6 invalid state cases
```

Negative controls include:

```text
partial provider/model binding
warm state without evidence
expired state without route
session-start state with a nonzero change count
warm-affinity reason with cold state
unknown route reason
```

## Verification commands

```powershell
python -m pytest .\tests\unit\contracts\test_route_contracts.py
python -m pytest .\tests\unit\routing\test_state.py
python -m ruff check .\src\auragateway\contracts\route.py .\src\auragateway\routing .\tests\unit\contracts\test_route_contracts.py .\tests\unit\routing\test_state.py
python -m ruff format --check .\src\auragateway\contracts\route.py .\src\auragateway\routing .\tests\unit\contracts\test_route_contracts.py .\tests\unit\routing\test_state.py
python -m mypy src tests
```

## Permitted claim

AuraGateway now has a deterministic, typed, metadata-only session-route state boundary with exact route reasons and invalid-state controls.

## Non-claims

This slice does not prove:

```text
provider cache hits
provider cache residency or TTL
safe route selection
route-thrash prevention across trajectories
quality non-inferiority
latency or cost improvement
A/B/C benchmark readiness
```
