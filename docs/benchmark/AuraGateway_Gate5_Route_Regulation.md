# AuraGateway Gate 5 Route Regulation Evidence

## Status

```text
proof_gate=Gate 5 — Route Policy
regulation_fixture_set=auragateway-gate5-route-regulation-v1
route_regulation_cases=5
retry_regulation_cases=8
negative_controls=9
gate_5_regulation_passed=true
measured_execution_permitted=false
provider_calls=none
```

This report records deterministic regulation evidence only. Gate 5 closure also depends on the previously merged session-route state and single-transition route-policy suites continuing to pass in the full repository validation.

## Boundary

The runtime path is:

```text
caller-proposed transition
    ↓
single-transition route policy
    ↓
route-history regulation
    ↓
existing state-transition function
```

Provider retry authorization is a separate path:

```text
retained provider-attempt history
    ↓
bounded retry regulation
    ↓
authorized retry metadata or blocked decision
```

Neither path autonomously selects a provider/model or invokes a provider.

## Deterministic evidence

Route regulation proves:

- warm-route preservation remains executable when no route-change limit is crossed;
- the first allowed provider/model change is executable;
- a second non-exempt provider/model change is blocked as route thrash;
- explicit benchmark-control transitions remain exempt;
- an already-blocked route-policy decision remains blocked.

Retry regulation proves:

- one bounded retry can follow a definite retryable failure;
- ambiguous responses block duplicate generation;
- non-retryable failures remain blocked;
- retry-budget exhaustion remains blocked;
- repeated recovery actions are rejected as invalid retries;
- request-fingerprint changes are not treated as retries;
- provider/model changes must return to route policy;
- successful attempts cannot be retried.

## Frozen artifact hashes

```text
regulation_cases.json:
2bf3aecf36cabf9a1002efd84d39037ee1e4ad640bd8408ea73b2ce624cee300

regulation_report.json:
4f74e25dc9b6abf6ba84206bc8d260481225f819afd6a653b30a2fd580766f88
```

The manifest contains both hashes and is verified before report reproduction.

## Commands

```powershell
python -m auragateway.routing.regulation_runner build --repo-root .
python -m auragateway.routing.regulation_runner verify --repo-root .
```

The normal release workflow should use `verify`. `build` is used only when intentionally creating a new frozen fixture/report/manifest version.

## Privacy and evidence limits

Retained fields are limited to:

- hashed session and logical-request identities;
- provider/model aliases;
- typed reason and decision codes;
- route state and route-change counts;
- provider error codes;
- retryability;
- recovery and evidence fingerprints;
- timestamps;
- artifact hashes.

The evidence excludes raw prompts, user messages, retrieved documents, model outputs, API keys, direct user identifiers, and raw provider payloads.

## Permitted claim

AuraGateway has locally validated deterministic route-history regulation, route-thrash blocking under the named default, bounded retry authorization, retry-budget enforcement, repeated-recovery detection, and ambiguous-response duplicate protection using fixed metadata-only fixtures.

## Non-claims

This evidence does not establish:

- provider cache residency or exact TTL;
- optimal provider/model selection;
- universal agent-loop or stagnation detection;
- quality non-inferiority;
- latency or cost improvement;
- A/B/C benchmark results;
- customer-data readiness;
- deployment or production readiness.
