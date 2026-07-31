# ADR: Accept explicit Triton attention-backend execution V1

- Status: Accepted
- Date: 2026-07-31
- Decision owner: AuraGateway local A/B/C qualification

## Context

Kaggle saved version `339181603` executed the merged model-free Q6 notebook
under one explicit, time-bounded, single-use authorization. The run completed
with terminal decision
`EXPLICIT_TRITON_ATTENTION_BACKEND_V1_PASSED`.

The inspection package binds the successful log, evidence ZIP, authorization,
consumption receipt, and inspection manifest. The evidence ZIP contains eight
safe members. Every member size and SHA-256 matches the bundle manifest.

## Decision

Accept the Q6 execution as evidence that the reviewed CUDA 12.9 target runtime
can discover and import the native vLLM `TRITON_ATTN` backend on Tesla T4,
validate the bounded decoder capability contract, and execute the exact
backend-owned model-free Triton primitive within the reviewed tolerance.

Close the single-use authorization lifecycle. Unchanged replay is prohibited.
Authorize repository implementation of the P3-P6 runtime diagnostic only.

## Consequences

The next gate is:

`DESIGN_AND_IMPLEMENT_P3_P6_RUNTIME_DIAGNOSTIC_V1`

That future diagnostic requires a separate implementation PR and a separate
runtime authorization before any worker, model, request, cache, or dual-worker
activity.

## Non-claims

This decision does not establish worker readiness, model loading, inference,
paged decoder attention, KV-cache behavior, causal masking, cache telemetry,
cache reset, dual-worker isolation, measured A/B/C effects, deployment, or
production readiness.
