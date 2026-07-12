# ADR-0005: Provider Telemetry Semantics

- **Status:** Accepted
- **Date:** 2026-07-12
- **Decision owners:** AuraGateway project maintainers
- **Applies from:** Phase 3
- **Supersedes:** None

## Context

AuraGateway must compare runtime behavior across providers and a local runtime without inventing a universal cache model. Providers expose materially different token-accounting fields. Local runtimes may expose timing and prompt-evaluation counts without exposing provider-style cached-token evidence.

Flattening these signals into `cache_hit`, one cache-token field, or zero-filled missing values would create false equivalence and permit unsupported cache, latency, or cost claims.

## Decision

AuraGateway will preserve provider-specific telemetry families and normalize them into a typed envelope that retains provenance and denominator meaning.

The initial semantic families are:

1. total provider input plus cached-input detail;
2. provider cache-creation, cache-read, and uncached-input components;
3. local prompt-evaluation count and timing;
4. explicit unavailable evidence.

Unknown values remain `None`. Missing values never become zero.

Local timing is classified as inferred local evidence. It cannot authorize a provider cached-token claim.

Cache, latency, and estimated-cost claims are authorized independently by a typed sufficiency gate. Missing pricing blocks cost claims without blocking otherwise valid cache or latency evidence.

Raw provider SDK objects and payloads remain inside adapter implementations and are not persisted.

## Consequences

### Positive

- Provider meaning survives normalization.
- Unsupported claims fail closed with explicit reason codes.
- Local timing remains useful without being overstated.
- Pricing changes can be versioned independently from token evidence.
- Future provider adapters have a stable typed target.

### Negative

- Provider adapters require explicit semantic mapping.
- Some cross-provider aggregate metrics remain unavailable.
- A live provider field change can block claims until recalibrated.
- More typed fields and fixtures are required than a universal cache boolean.

## Required verification

Implementation must prove that:

- valid provider fixtures map into typed contracts;
- missing cache fields remain `None`;
- invalid denominators produce `CACHE_SEMANTICS_MISMATCH`;
- local timing cannot authorize provider cache claims;
- missing latency blocks only latency claims;
- missing pricing blocks only estimated-cost claims when token evidence is otherwise valid;
- equivalent JSON key ordering produces equivalent typed meaning;
- raw provider payload fields are rejected at the contract boundary.

## Claim boundary

Gate 4 fixture evidence validates harness behavior only. It does not prove live provider cache reuse, current provider pricing, provider TTL, provider scheduling, latency savings, cost savings, or benchmark readiness.
