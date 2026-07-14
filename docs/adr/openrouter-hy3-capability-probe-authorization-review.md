# ADR: OpenRouter Hy3 Capability-Probe Authorization Review

- **Status:** Accepted
- **Date:** 2026-07-14
- **Decision ID:** `openrouter-hy3-capability-probe-authorization-review-v1`

## Context

The OpenRouter adapter dry run passed without network or credential access. The next boundary is a
strictly bounded two-call Hy3 free-route capability probe. The probe must determine whether
OpenRouter returns numeric cache telemetry and whether an exact repeated prefix produces a cache
write or warm cache read.

The route is time-limited. The review therefore prioritizes a small measurement-channel test before
any A/B/C pilot.

## Decision

Implement the explicit-key HTTP transport and freeze the activation policy, but keep live execution
inactive in this PR.

The future probe has two logical calls:

```text
cold_probe
warm_probe
```

It permits at most four inference attempts and at most one transient replacement for each logical
call. Replacement is permitted only for HTTP 429, 502, 524, or 529 before a provider success. A
successful inference response is never repeated, even when cache telemetry is absent, null, zero, or
later generation metadata is unusable.

Generation metadata is fetched once by generation ID. The implementation does not poll or repeat a
successful inference when generation metadata fails.

## Free-tier limit boundary

`GET /api/v1/key` exposes credit-limit and free-tier metadata. It does not provide an exact count of
remaining free-model requests, and successful inference responses do not carry rate-limit headers.
The local four-attempt ceiling is therefore authoritative and independent of any assumed platform
quota.

## Privacy boundary

Every future request requires:

```text
provider.data_collection = deny
provider.zdr = true
provider.order absent
synthetic public-safe content only
```

If these controls leave no eligible route, the probe closes. Privacy controls are not relaxed to
obtain a result.

## Promotion boundary

The capability probe can permit only a later pilot authorization review. It cannot authorize the
pilot directly.

Promotion requires:

```text
two retained successful calls
numeric cache telemetry
positive cache write or warm cache read
reconciled model, provider, generation, and session identity
```

Absent, null, numeric zero, and latency do not prove cache use.

## TLA+ decision

Do not add a TLA+ toolchain for this finite state machine.

Instead, retain an executable exhaustive state model in normal Python CI. It explores every reachable
state, validates the four-attempt and two-success ceilings, proves terminal authorization consumption,
and blocks promotion without positive telemetry and stable route identity.

This is not a claim that TLA+ model checking occurred. The decision is that a second formal-language
artifact would duplicate a small executable model while increasing maintenance and toolchain cost.

## Consequences

- The next PR may activate exactly one bounded capability probe.
- No live provider call is authorized by this review.
- No credential is read by this review.
- No automatic HTTP retry exists in the transport.
- The closed Groq lineage and the two earlier OpenRouter review lineages remain immutable.
