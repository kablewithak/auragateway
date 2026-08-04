# AuraGateway CU129 P3-P6 Runtime Diagnostic V5

## Objective

Repair the accepted V4 P6 harness divergence without changing the model,
tokenizer, runtime, attention backend, request budget, privacy boundary, or
accepted P3-P5 behavior.

## Accepted predecessor

- V4 saved version: `340120168`
- Completed probes: P3, P4, P5
- Failed probe: P6
- First divergence:
  `P6_WORKER_1_ROUTE_STRUCTURED_RESPONSE_OBJECT_MISMATCH`
- V4 authorization: consumed and non-reusable

## V5 intervention

V5 separates model-output correctness from route realization. P4 owns exact
structured output. P6 owns transport, response-envelope, worker identity, and
metric attribution. Every fallible P6 boundary writes an atomic checkpoint.

## Runtime evidence additions

- `runtime_native_origin_report_v5.json`
- `p6_stage_checkpoint_report_v5.json`
- worker-specific attempted/completed counters
- precise P6 failure codes
- counter-derived request activity

## Fixed execution budget

- Kaggle sessions: 1
- runtime installs: 1
- import-closure probes: 1
- model loads: 3
- worker starts: 3
- model requests: 5
- output tokens per request: 32
- network requests: 0
- hidden retries: 0
- external spend: R0 / $0

## Acceptance boundary

The implementation is production-shaped and repository validated only. Runtime
execution requires a separately implemented, merged, single-use V5 authorization
issuer. Measured A/B/C remains blocked until V5 evidence is preserved and
accepted.
