# ADR: P3-P6 Runtime Diagnostic V5 Typed Route Checkpoints

**Date:** 2026-08-04
**Status:** Accepted for repository implementation
**Source main:** `40b3530a763465fee0f7e27db17e9c444436ca18`

## Context

The governed V4 run accepted P3, P4, and P5, then failed during the first P6
route request. Worker 1 completed the HTTP request, but the model-generated JSON
did not exactly equal the route object in the user message. The V4 harness
raised before returning the transport and metric record, did not attempt worker
2, discarded partial P6 evidence, emitted the broad
`P3_P6_DUAL_WORKER_ISOLATION_FAILED` code, and incorrectly reported that no
model request had been performed.

P6 is an environment, transport, and metric-isolation probe. It must not depend
on model prompt-following semantics already covered by P4.

## Decision

Implement V5 with a harness-derived route acknowledgement:

1. reserve the bounded request action;
2. persist a worker-specific attempt checkpoint before the POST;
3. complete the loopback HTTP request;
4. persist transport completion;
5. validate the standard response envelope and model identity;
6. attribute target and non-target metric deltas;
7. reconcile global and per-worker request counters.

P4 retains exact structured-output equality. P6 records only a content hash and
never uses model semantics as route proof.

V5 also adds:

- atomic checkpoint and terminal evidence writes;
- `p6_stage_checkpoint_report_v5.json`;
- precise worker-specific transport, response, and metric failure codes;
- separate process, GPU, and port decisions;
- critical native-origin inspection across both worker process trees;
- rejection of CUDA driver stub origins;
- counter-derived `model_requests_performed` fields.

## Alternatives rejected

- Prompt refinement: preserves the brittle model-generation dependency.
- Hidden retry: violates the fixed action budget and diagnostic causality.
- Schema-constrained route generation: still couples routing proof to generation.
- Custom server endpoint: increases server coupling and change cost.
- Ignoring responses: would fail to validate the transport envelope.

## Consequences

V5 can preserve valid partial evidence at the exact failure boundary. A content
mismatch can no longer erase proof that a request reached the intended worker.
P6 still fails closed on transport, response envelope, metric attribution,
process/GPU/port isolation, native-origin closure, teardown, or counter drift.

## Non-claims

This ADR does not authorize runtime execution, establish P6 success, qualify the
measured A/B/C experiment, prove quality non-inferiority, or claim production
readiness.
