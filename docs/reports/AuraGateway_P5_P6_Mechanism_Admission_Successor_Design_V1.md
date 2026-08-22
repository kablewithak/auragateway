# AuraGateway P5/P6 Mechanism-Admission Successor Design V1

## Decision

Design the next exact-runtime P5/P6 implementation as a successor of Exact-Runtime Requalification V2. Preserve the V2 runtime, request identity, tokenization, telemetry, worker attribution, budgets, teardown, and proof criteria. Change only the control boundary that currently lets semantic mismatch abort already-valid mechanism evidence.

## Current governed state

- C4 semantic canary: `NOT_QUALIFIED`.
- C4 mechanism admission: `QUALIFIED`.
- P5 exact-runtime requalification: not established.
- P6 exact-runtime requalification: not established.
- Variance pilot: not accepted.
- Final A/B/C: not executed.
- New execution authorization: absent.

## Predecessor

Exact-Runtime P5/P6 Requalification V2 is the implementation base because it already contains the current exact-runtime line:

- Python 3.12
- cu129
- torch 2.11.0+cu129
- transformers 5.14.1
- triton 3.6.0
- vLLM distribution 0.25.1+cu129 / semantic version 0.25.1
- Kaggle T4 x2 topology
- Qwen/Qwen2.5-0.5B-Instruct revision `7ae557604adf67be50417f59c2c2f167def9a775`
- model directory SHA-256 `84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94`

V2 remains immutable predecessor evidence.

## Exact blocker

The current request helper collects mechanism-relevant evidence before semantic validation, but then raises if the model response differs from the exact expected JSON object. That exception prevents the request result from reaching downstream P5 logic.

The problem is therefore not that P5 lacks telemetry. It is that semantic failure is still a control-flow prerequisite for returning telemetry.

## Successor boundary

The successor must split one response into two independent views.

### Semantic observation

Allowed states:

- `EXACT_MATCH`
- `VALID_JSON_MISMATCH`
- `NON_OBJECT_JSON`
- `INVALID_JSON`

Semantic state is recorded and preserved. It does not block mechanism evidence solely because content is wrong or not valid JSON.

### Mechanism admission

Still blocking:

- HTTP/request failure
- invalid response envelope
- finish reason other than `stop`
- invalid prompt/completion token accounting
- request/token identity drift
- missing or ambiguous request metric window
- missing output provenance
- hidden retries
- worker identity ambiguity
- request-count mismatch
- teardown/cleanup failure

## P5 remains unchanged

Mechanism admission is not P5 proof. P5 must still prove attributable cache behavior using the frozen exact-runtime criteria, including cold zero-hit state, warm positive local reuse, reduced warm local compute, negative-prefix control, post-reset cold state, cross-worker cold state, and zero external KV transfer.

Semantic state cannot count as cache evidence.

## P6 remains unchanged

Mechanism admission is not P6 proof. P6 must still prove worker/process/GPU isolation, request-scoped metric movement on only the intended worker, no hidden fallback, cross-worker cold state, worker-1 retained state, exact request reconciliation, output attribution, and teardown.

Model semantics cannot count as route proof.

## Required regression

The implementation must include a fixed regression case where the response envelope, request identity, token identity, metric attribution, and worker identity are healthy but the model returns the known wrong semantic object.

Expected result:

- semantic observation: negative;
- mechanism evidence: retained;
- no failure solely because semantic equality is false.

Separate fixed cases must prove that transport/envelope/identity/metric/worker/lifecycle failures remain blocking.

## Authorization boundary

The V2 authorization scope is not reusable. The successor requires a distinct scope:

`P5_P6_MECHANISM_ADMISSION_SUCCESSOR_V1`

This design does not issue execution authority. No model, GPU, or Kaggle execution is permitted by this tranche.

## Candidate boundary

Authored paths:

1. `src/auragateway/local_abc/p5_p6_mechanism_admission_successor_design_v1.py`
2. `tests/unit/local_abc/test_p5_p6_mechanism_admission_successor_design_v1.py`
3. `docs/adr/2026-08-22-local-abc-p5-p6-mechanism-admission-successor-design-v1.md`
4. `docs/reports/AuraGateway_P5_P6_Mechanism_Admission_Successor_Design_V1.md`
5. `docs/runbooks/local_abc_p5_p6_mechanism_admission_successor_design_v1.md`

Producer-owned generated paths:

6. `benchmarks/local_abc/auragateway_p5_p6_mechanism_admission_successor_design_v1.json`
7. `benchmarks/local_abc/auragateway_p5_p6_mechanism_admission_successor_design_v1_review.json`

## Downstream-aware implementation order

The next tranche should finalize authored implementation bytes first, then run formatting/lint/type checks, then regenerate notebook/review/record identities once, then rerun deterministic generation and focused regressions. A semantic-boundary fix must not be accepted if it predictably creates format, line-length, typing, generated-hash, or authorization drift.

## Non-claims

This design does not implement the runtime successor, requalify P5/P6, authorize live execution, establish variance adequacy, execute final A/B/C, establish quality non-inferiority, or claim production readiness.

## Next gate

`IMPLEMENT_AND_MERGE_P5_P6_MECHANISM_ADMISSION_SUCCESSOR_V1`
