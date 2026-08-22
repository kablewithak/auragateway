# ADR: P5/P6 Mechanism-Admission Transaction-Bound Authorization Reconciliation V1

**Date:** 2026-08-23
**Status:** Accepted reconciliation design; implementation not yet authorized
**Base main:** `f33c835414b89dca15976e30877d7f0ebfa96e06`

## Context

The P5/P6 Mechanism-Admission Successor correctly uses Exact-Runtime P5/P6 Requalification V2 as its behavioral predecessor. That predecessor carries the required current runtime, P5 cache-attribution criteria, P6 worker/state-isolation criteria, request accounting, and teardown semantics.

However, Exact-Runtime V2 is not the current authorization-architecture predecessor. PR #239 superseded its authorization-specific Kaggle transport with `TRANSACTION_BOUND_EXECUTION_ARTIFACT`. PRs #240 and #241 implemented and integrated that architecture, including zero authorization-specific Kaggle inputs and zero authorization producer notebooks. Later governed authorization tranches continued that transaction-bound pattern.

The Mechanism-Admission Successor design inherited the V2 authorization transport without reconciling the later superseding authorization authority. The implementation and PR #291 then remained internally consistent with that stale transport decision.

No live successor authorization was issued and no governed runtime execution occurred under PR #291. The regression is therefore recoverable entirely inside the static control plane.

## Decision

Use two distinct predecessors:

- behavioral predecessor: `EXACT_RUNTIME_P5_P6_REQUALIFICATION_V2`;
- authorization predecessor: `TRANSACTION_BOUND_EXECUTION_AUTHORIZATION_V1`.

Restore the transaction-bound execution-authorization architecture for the current mechanism-admission successor.

The successor authorization implementation SHALL require:

- fresh explicit human authority;
- `RETYPE_DYNAMIC_SHA256_CHALLENGE` with exact manual retype;
- canonical authorization bytes;
- transaction ID derived from `SHA256(CANONICAL_AUTHORIZATION_BYTES)`;
- exact mechanism-admission implementation and runtime payload identity;
- exact current runtime/model identity;
- exact 6 request / 3 worker-start / 3 model-load ceiling;
- zero hidden retries, replacement workers, external network requests, benchmark requests, and external spend;
- deterministic transaction-bound executable generation;
- authorization admission before runtime installation/model construction;
- durable platform observation after executable generation and before the single Save & Run All;
- terminalization after every attempted execution.

The successor SHALL NOT require:

- an authorization-specific Kaggle input;
- an authorization producer/materializer notebook;
- runtime authorization filename discovery;
- a manually constructed confirmation JSON file;
- pre-issuance Kaggle platform observation as an authorization dependency.

Kaggle input roles remain limited to durable runtime and model snapshot inputs.

## Mechanism semantics preserved

This reconciliation does not reopen the mechanism-admission design. The following remain frozen:

- semantic states: `EXACT_MATCH`, `VALID_JSON_MISMATCH`, `NON_OBJECT_JSON`, `INVALID_JSON`;
- semantic mismatch does not block mechanism evidence;
- invalid JSON does not itself block mechanism evidence;
- `finish_reason == stop` remains mandatory;
- response-content provenance remains digest-only;
- raw output logging remains prohibited;
- P5 does not use semantic state as cache proof;
- P6 does not use semantic state as route proof;
- P5 and P6 acceptance criteria are not relaxed.

## PR #291 disposition

PR #291 and its exact-flat transport artifacts remain immutable repository history. Their static disposition becomes:

`IMPLEMENTED_BUT_SUPERSEDED_BEFORE_LIVE_ISSUANCE`

They are not deleted, rewritten, or promoted as current execution authority. No live authorization was issued from that topology.

## Safety boundary

This design tranche performs no Kaggle execution, GPU execution, model request, worker start, model load, or live authorization issuance. It does not mutate the current mechanism-admission runtime or the PR #291 issuer/transport files.

## Next gate

`IMPLEMENT_AND_MERGE_P5_P6_MECHANISM_ADMISSION_TRANSACTION_BOUND_AUTHORIZATION_V1`
