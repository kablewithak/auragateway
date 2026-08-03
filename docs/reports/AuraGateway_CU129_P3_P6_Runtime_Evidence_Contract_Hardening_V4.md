# AuraGateway P3-P6 Runtime Evidence Contract Hardening V4

## Problem

V3 produced a false negative after the worker had already reached readiness,
returned the exact served-model inventory and emitted the vLLM 0.19.1
`TRITON_ATTN` startup-selection line.

The failed classifier was not line-local and required a spaced phrase that does
not occur inside `AttentionBackendEnum`.

## V4 implementation

The V4 generated runtime adds five evidence boundaries:

1. Exact line-local backend-marker classification with explicit rejection of
   CLI echo, source literals, split-stream coincidence and multiple matches.
2. Capture finalization before terminal failure diagnostics are serialized.
3. Worker process and GPU identity including generation, PID, parent PID,
   process start ticks, GPU UUID and PCI bus ID.
4. Structured teardown evidence covering process trees, GPU processes, ports,
   capture threads and bounded GPU-memory return.
5. A generated notebook wrapper that verifies the exact runtime-script SHA-256
   before compiling and executing it.

The runtime source identity and teardown reports are allowlisted members of the
bounded evidence ZIP.

## Fixed diagnostic cases

Focused tests cover exact and logger-prefixed markers, CLI echo, source
literals, wrong backends, split streams, ambiguity, capture finalization,
serialization order, runtime wrapper identity, worker identity, teardown fields,
authority drift, generated drift and exact candidate boundaries.

## State

```text
implementation: IMPLEMENTED_NOT_EXECUTED
runtime authorization: false
Kaggle execution: false
GPU execution: false
model requests: 0
network requests: 0
external spend: 0
```

## Non-claims

This tranche does not establish formal P3 success, request-level attention
execution, P4, P5, P6, complete native-library provenance, saved-version
notebook byte identity, deployment readiness or production readiness.
