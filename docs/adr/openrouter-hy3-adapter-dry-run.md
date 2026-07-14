# ADR: OpenRouter Provider Adapter Fixture-Only Dry Run

- **Status:** Accepted
- **Date:** 2026-07-14
- **Decision ID:** `openrouter-hy3-adapter-dry-run-v1`

## Context

The identifiability review permits a generic OpenRouter adapter and dry-run harness but authorizes no
credential access or live provider call.

The OpenRouter boundary must preserve normalized cache reads, cache writes, sticky-session identity,
resolved model, resolved provider, and generation metadata without describing those values as
Tencent-direct telemetry.

## Decision

Implement `OpenRouterProviderAdapter` behind an injected transport protocol.

The adapter:

- uses `tencent/hy3:free` as configuration, not as a core abstraction;
- emits a new extensible typed envelope while reusing protected prompt/output containers;
- retains cache-write and route data in an OpenRouter-specific typed observation envelope;
- requires `data_collection=deny` and `zdr=true`;
- prohibits manual provider order;
- requires generation metadata to reconcile model and session identity;
- preserves absent, null, zero, and positive cache fields;
- rejects invalid numeric types and generation identity drift;
- owns no HTTP client, key lookup, or retry loop in this slice.

## TLA+ checkpoint

Do not add a formal model yet. Reassess after the capability-probe authorization introduces the real
attempt-budget, transient-replacement, evidence-retention, and authorization-consumption state
machine.

## Consequences

The adapter boundary is locally testable and provider-neutral at the core seam. Live telemetry,
privacy-compatible route availability, endpoint count, cache use, Condition C effect, and benchmark
eligibility remain unproven.
