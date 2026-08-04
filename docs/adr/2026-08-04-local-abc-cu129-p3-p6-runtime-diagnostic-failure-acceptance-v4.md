# ADR: Accept P3-P6 runtime diagnostic V4 failure

Date: 2026-08-04

## Status

Accepted for repository implementation.

## Context

The governed V4 Kaggle saved version `340120168` completed P3, P4, and P5,
then failed during P6. The runtime emitted a complete terminal archive with
clean worker teardown, clean scratch removal, zero network requests, zero
hidden retries, and zero external spend.

The broad runtime failure code was
`P3_P6_DUAL_WORKER_ISOLATION_FAILED`. The first observable divergence was
narrower: the first P6 route request reached worker 1, returned non-matching
structured JSON, and failed the exact response-object equality contract before
the worker 2 route request executed.

The evidence also exposes three harness-quality defects:

1. the P6 terminal stub reports `model_requests_performed=false` despite the
   global request counter and worker HTTP trace proving one P6 request attempt;
2. the broad failure taxonomy conflates process/GPU isolation with route
   response validation;
3. partial P6 stage results are discarded when the complete P6 report cannot
   be written.

## Decision

Accept the run as a valid governed diagnostic failure.

Preserve the exact authorization, consumption receipt, lifecycle receipt,
intake archive, runtime archive, terminal log, launch manifest, saved-version
reference, limitations, root-cause analysis, duplicate exclusion, intake
receipt, and all runtime evidence members.

Accept the following results:

- P3 explicit `TRITON_ATTN` startup;
- P4 deterministic structured inference;
- P5 prefix-cache reuse;
- P5 reset through a full worker restart;
- dual-worker startup with distinct GPU identities and line-local backend
  markers;
- worker teardown and scratch cleanup.

Do not accept P6 route or metric isolation.

The next implementation must add stage-local P6 checkpoints, precise error
labels, per-worker attempted/completed request counters, and a constrained or
deterministic route acknowledgement contract.

## Rejected alternatives

- Replaying the unchanged notebook: rejected because the authorization was
  single-use and is consumed.
- Reclassifying the run as interrupted: rejected because the governed terminal
  report is complete and explicitly failed.
- Treating all P6 work as uninformative: rejected because worker startup,
  backend identity, request counts, and teardown evidence remain diagnostic.
- Weakening exact structured-output equality without a replacement contract:
  rejected because that would hide a real harness boundary.
- Advancing directly to measured A/B/C execution: rejected because P6 remains
  incomplete.

## Consequences

The runtime compatibility boundary is substantially narrower than before:
installation, import closure, explicit backend realization, deterministic
inference, cache reuse, and reset are established.

The remaining work is a P6 harness-design problem, not a broad CUDA,
wheelhouse, backend-selection, or cache-runtime redesign.

No runtime execution is authorized by this acceptance package.
