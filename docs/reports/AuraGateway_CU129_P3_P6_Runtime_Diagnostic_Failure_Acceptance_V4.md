# AuraGateway P3-P6 Runtime Diagnostic Failure Acceptance V4

## Classification

Saved version `340120168` is accepted as a valid governed diagnostic failure.

```text
Lifecycle outcome: FAILED
Completed probes: P3, P4, P5
Failed probe: P6
Reported code: P3_P6_DUAL_WORKER_ISOLATION_FAILED
First divergence: P6_WORKER_1_ROUTE_STRUCTURED_RESPONSE_OBJECT_MISMATCH
Evidence disposition: ACCEPTED_DIAGNOSTIC_FAILURE
```

## Established behavior

- exact governed notebook and runtime-script identities were executed;
- offline CUDA 12.9 runtime installation passed;
- process-tree import closure passed;
- P3 explicit `TRITON_ATTN` startup passed;
- P4 deterministic structured inference passed;
- P5 same-worker prefix-cache reuse passed;
- P5 full-process restart reset passed;
- three worker starts and three model loads remained within budget;
- both terminal workers retained distinct GPU identities and line-local
  `TRITON_ATTN` markers;
- all worker teardown checks passed;
- scratch cleanup passed;
- no customer data, credentials, network requests, hidden retries, benchmark
  trajectories, or external spend were recorded.

## Failure trace

P4 and P5 consumed three model requests. The global counter is four. Worker 1
generation 2 retained two completion POSTs, covering the post-reset request and
the first P6 route request. Worker 2 retained no completion POST. The terminal
safe message is `structured response differs from the requested object`.

The high-confidence inference is that the first P6 route request reached worker
1 and failed the exact structured-response equality check before the worker 2
route request executed.

## Evidence defects

1. The generated P6 terminal stub says no model request was performed.
2. The broad P6 failure code hides the route-response divergence.
3. Successful intermediate P6 stages are not serialized independently.

These are evidence-contract defects. They do not invalidate the terminal
failure or the accepted P3-P5 results.

## Next gate

`design_and_merge_p3_p6_runtime_diagnostic_v5`

The V5 boundary must add stage-local P6 reports, precise failure taxonomy,
per-worker request accounting, and schema-constrained or deterministic route
acknowledgement.

## Non-claims

- P6 route isolation did not pass.
- Worker 2 did not receive its route request.
- Full dual-worker metric isolation is not established.
- The exact mismatching model output was intentionally not retained.
- Measured A/B/C execution did not occur.
- The consumed authorization cannot be reused.
- Deployment and production readiness are not established.
