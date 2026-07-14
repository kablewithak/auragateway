# ADR: OpenRouter Hy3 Identifiability Review

- **Status:** Accepted
- **Date:** 2026-07-14
- **Decision ID:** `openrouter-hy3-identifiability-review-v1`

## Context

AuraGateway v2 core scope closed after Groq omitted the required billing cache field from both
successful raw responses. The new 48-hour extension asks whether Tencent Hy3 can provide a usable
measurement channel through OpenRouter's time-limited free route.

Hy3 is the requested model. OpenRouter is the gateway, routing authority, raw HTTP boundary, and
telemetry authority.

The extension must not reopen or rewrite the closed Groq evidence lineage.

## Decision

Proceed with a generic `OpenRouterProviderAdapter` and dry-run harness.

Do not authorize a live call, pilot, or retained benchmark in this review.

Freeze the conditions as:

```text
A: unstable prefix + unique session ID per request
B: deterministic stable prefix + unique session ID per request
C: deterministic stable prefix + stable AuraGateway-derived session ID
```

OpenRouter documents that a supplied `session_id` replaces the message-derived sticky key and
activates sticky routing after any successful request. A and B therefore use unique session IDs to
suppress retained affinity. C uses a stable session ID to enable retained affinity.

Do not specify `provider.order` in the affinity experiment because OpenRouter documents that manual
provider order disables sticky routing.

Use OpenRouter-normalized telemetry and generation metadata. Do not describe it as Tencent-direct
telemetry.

Require `data_collection: deny` and `zdr: true` for any future live request. If no eligible free route
remains under those controls, close the path rather than weakening privacy.

## Consequences

### Positive

- A versus B and B versus C have separate controlled interventions.
- Hy3 remains configuration behind a model-agnostic provider adapter.
- Missing, null, zero, and positive telemetry remain distinct.
- Route and cache claims stay bounded to OpenRouter.
- The free route can be used without making paid replication a release gate.

### Costs

- Route identity and privacy compatibility remain unverified until bounded preflight.
- Endpoint count remains unknown.
- The time-limited route reduces later reproducibility.
- Condition C effectiveness remains blocked until multiple valid live pairs exist.

## TLA+ decision

Do not model the repository with TLA+.

Reassess a small execution-state specification before live authorization after the retry,
replacement-attempt, authorization-consumption, and promotion logic exists in Python.
