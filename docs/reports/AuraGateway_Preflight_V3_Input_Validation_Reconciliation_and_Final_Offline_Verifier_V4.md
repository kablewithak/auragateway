# AuraGateway Preflight V3 input-validation reconciliation and final offline verifier V4

## Executive result

Saved version `341197546` is retained as a valid diagnostic execution and an invalid runtime
qualification result. Its first material divergence was an impossible historical-receipt schema
expectation, not a runtime failure.

Classification:

`DIAGNOSTIC_HARNESS_DEFECT / BACKPROJECTED_UPSTREAM_RECEIPT_SEMANTIC_REQUIREMENT`

`runtime_incompatibility_established=false`

## Execution trace

Intended:
historical input identity -> producer receipt validation -> target creation -> offline install ->
controlled startup -> native inventory -> static provenance -> native import -> dynamic provenance ->
CUDA capability.

Observed:
historical input identity -> producer receipt loaded -> V3 asks receipt for a later consumer-policy
field -> field absent -> `input_validation=FAILED` -> all runtime roles blocked.

Package installation did not start. No model, worker, request, P5/P6, pilot, or benchmark execution
occurred.

## Reconciliation

V4 keeps the historical receipt byte-exact and validates only producer-owned materialization facts.
Current verifier policy is represented independently and remains authoritative for controlled Python
startup, native loader provenance, and the rule that successful native import alone is insufficient.

The exact historical materialization receipt is now a regression fixture. Its SHA and semantic facts
must pass the local pre-execution compatibility gate before a later authorization can be issued.

## Maintainability rule

Every cross-version input field must have one explicit owner:

- producer evidence field -> emitted by the historical producer artifact;
- consumer policy field -> asserted by current repository authority.

A consumer must not retroactively demand a new field from immutable historical evidence.

## Safety boundary

V4 is `IMPLEMENTED_NOT_EXECUTED`.

All remain false:

- `exact_runtime_offline_verified`
- `p5_p6_exact_runtime_requalified`
- `runtime_execution_authorized`
- `pilot_execution_authorized`
- `final_measured_abc_execution_authorized`
- `next_expensive_execution_permitted`

## Next gate

Implement and merge a V4-specific single-use execution authorization issuer only after V4 repository
acceptance and merged-main pre-execution validation.
