# ADR: P5/P6 Mechanism-Admission Successor Design V1

**Date:** 2026-08-22
**Status:** Accepted design; implementation not yet authorized by this ADR
**Base main:** `f534a27d3e07fc699c7fb1e4e257730cc71590f4`
**Decision:** Build the next exact-runtime P5/P6 implementation from Requalification V2 while separating semantic observation from mechanism admission.

## Context

PR #288 established Qualification Contract V2 and the static C4 mechanism-admission assessment.
The governed state is deliberately split:

- C4 semantic canary: `NOT_QUALIFIED`.
- C4 mechanism admission: `QUALIFIED`.
- P5: not requalified on the exact current runtime.
- P6: not requalified on the exact current runtime.
- New execution authorization: absent.

Exact-Runtime P5/P6 Requalification V2 is the correct implementation predecessor. It already binds the current Python 3.12 / cu129 / vLLM 0.25.1 runtime line, the exact model and tokenizer identities, request-scoped cache telemetry, worker/process/GPU attribution, bounded request accounting, teardown, and repaired authorization transport.

The remaining control-flow defect is narrower. The V2 runtime obtains request token identity, pre-request metrics, a model response, post-request metrics, usage, and response content, then calls `validate_structured_response()`. That helper raises when model content is not the exact requested object. Because `run_structured_request()` does not return after that exception, already-collected mechanism evidence cannot reach the downstream P5 path.

That behavior conflicts with Qualification Contract V2. Exact-object equality and JSON validity are semantic diagnostics only. They are not P5 cache proof and are not P6 route proof.

## Decision

Create a new successor implementation rather than modify V2 in place.

V2 remains immutable predecessor evidence. The successor must inherit its exact-runtime, telemetry, attribution, lifecycle, and evidence controls unless a separately reviewed design explicitly changes them.

The successor runtime must introduce a typed semantic observation with these states:

- `EXACT_MATCH`
- `VALID_JSON_MISMATCH`
- `NON_OBJECT_JSON`
- `INVALID_JSON`

Semantic observation must be total for any non-empty response content admitted by the response-envelope boundary. Model-content disagreement alone must not raise an execution failure.

The mechanism-admission boundary remains fail-closed. The successor must still reject invalid transport, invalid response envelopes, non-`stop` finish reasons, invalid token accounting, request or token identity drift, ambiguous metric attribution, hidden retries, worker-identity ambiguity, request-count mismatch, or teardown failure.

P5 acceptance remains unchanged. It must continue to require attributable cold/warm/reset/cross-worker cache behavior, the negative-prefix bound, zero external KV transfer, and the existing exact-runtime token/metric identity rules. Semantic state must not become cache proof.

P6 acceptance remains unchanged. It must continue to require disjoint worker/process/GPU realization, request-scoped metric movement only on the intended worker, no hidden fallback, cross-worker cold-state evidence, worker-1 retention, exact request reconciliation, and teardown. Model semantics must not become route proof.

## Required implementation seam

The successor implementation must replace exception-driven semantic validation with a diagnostic observer and update `run_structured_request()` so that:

1. transport and request accounting execute;
2. response-envelope validation executes;
3. token and metric evidence are retained;
4. output provenance is retained as a digest without raw-output logging;
5. semantic state is recorded independently;
6. mechanism evidence is returned even when semantic state is negative;
7. downstream P5/P6 evaluators consume only their frozen mechanism criteria.

A regression case must explicitly prove this boundary:

`healthy transport + valid request identity + valid metric attribution + wrong semantic object`

must preserve mechanism evidence and record a negative semantic observation without aborting solely because of semantics.

The opposite boundary must also be tested. Transport failure, invalid envelope, non-`stop` finish reason, token-identity drift, metric ambiguity, hidden retries, worker misattribution, or teardown failure must remain blocking.

## Authorization

No V2 execution authorization may be reused for the successor. Changed runtime bytes require a fresh authorization scope:

`P5_P6_MECHANISM_ADMISSION_SUCCESSOR_V1`

This design does not issue that authorization. The implementation tranche must also remain non-executable until a separate successor authorization issuer is designed, reviewed, and merged.

## Downstream effects

Implementation will change the successor runtime-template bytes and therefore the generated notebook hash, implementation review, implementation record, and any artifact binding the runtime-script identity. Those generated artifacts must be regenerated from final authored bytes after formatting and static validation.

The implementation should not change the exact request corpus, 899-token full prompt, 880-token reusable prefix, 16-token block size, 55 reusable cache blocks, current runtime versions, P5 acceptance criteria, P6 acceptance criteria, hidden-retry budget, or execution-authority posture unless new evidence invalidates one of those constraints.

## Alternatives rejected

### Keep V2 behavior and require semantic equality before P5

Rejected. That repeats the already-observed false-negative control boundary and makes semantic correctness an accidental prerequisite for mechanism measurement.

### Relax P5 or P6 acceptance criteria

Rejected. Gate B changes admission into mechanism measurement; it does not weaken the mechanism proof obligations.

### Change the corpus and the qualification contract together

Rejected. Static re-entry work established adequate cache geometry. The known blocker is control-flow coupling, not cacheable-prefix length.

### Reuse V2 authorization

Rejected. Authorization is scope- and identity-bound and cannot silently survive changed runtime bytes.

## Consequences

The implementation can preserve a semantic negative while still collecting interpretable cache and route evidence. This removes a false gating dependency without converting semantic disagreement into positive mechanism proof.

The cost is an additional successor lineage and fresh authorization lifecycle. That cost is accepted because it keeps historical evidence immutable and makes the scientific boundary inspectable.

## Non-claims

This ADR does not implement or execute the successor. It does not requalify P5 or P6, establish variance adequacy, execute final A/B/C, establish quality non-inferiority, or authorize GPU/Kaggle/model execution.

## Next gate

`IMPLEMENT_AND_MERGE_P5_P6_MECHANISM_ADMISSION_SUCCESSOR_V1`
