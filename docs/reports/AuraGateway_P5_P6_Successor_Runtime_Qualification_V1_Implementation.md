# AuraGateway P5/P6 Successor Runtime Qualification V1 — Implementation Report

## Status

`IMPLEMENTED_NOT_EXECUTED`

This tranche composes the accepted P4 V2 environment/output boundary with the V5
P5/P6 evidence harness. It creates no runtime authorization and performs no runtime
execution.

## What changed

The successor runtime now:

- uses P4 V2-style CUDA stub filtering and `LD_PRELOAD` removal;
- preserves V5's 4096 model length, 0.85 GPU memory utilization, max 8 sequences,
  explicit `TRITON_ATTN`, and two-worker topology;
- runs one case-A P4 canary and reuses it as the P5 cold baseline;
- keeps V5's long synthetic deterministic context before the final case-A object;
- uses token telemetry, not latency, as primary P5 proof;
- requires a full worker-process restart and fresh backend/native-origin validation;
- proves P6 with transport acknowledgement plus target/non-target metric deltas;
- preserves per-worker attempted/completed counters before fallible route validation;
- fails closed on ambiguous relevant metric-series cardinality;
- retains only hashes/structured evidence rather than raw prompts or raw outputs;
- treats teardown or scratch-cleanup failure as overall execution failure.

## Governed budget

The runtime ceiling is one Kaggle session, one runtime install, one import-closure
probe, three worker starts/model loads, and five model requests. Hidden retries,
replacement workers, benchmark trajectories, network access, credentials, customer
data, and external spend are prohibited.

## P5 acceptance

The P4 canary is the cold request. The same composed payload is used for warm and
post-restart requests.

Required directionality:

- cold cached-prefix tokens = 0;
- warm cached-prefix tokens > 0;
- warm computed-prefill tokens < cold computed-prefill tokens;
- post-restart cached-prefix tokens = 0;
- post-restart computed-prefill tokens > 0;
- old/new worker process identity differs;
- backend and governed native origins are revalidated after restart.

Exact total prompt-token equality across independent processes is not required.

## P6 acceptance

Worker 1 is GPU 0 / port 8001. Worker 2 is GPU 1 / port 8002.

For each routed request both worker metric endpoints are snapshotted. The target
worker must show positive prompt-token delta and the non-target worker must show
zero prompt-token delta. Each worker must reconcile exactly one attempted and one
completed P6 request.

Unexpected model content may invalidate only the response-envelope boundary if the
envelope itself is malformed. Semantic equality with the P4 target object is not
used as route proof.

## Validation boundary

The producer owns four generated artifacts:

- successor request JSON;
- implementation review JSON;
- single-cell notebook;
- implementation record JSON.

Six authored files plus those four generated files form the ten-path candidate
boundary.

The exact user repository must still run its native Ruff, format, mypy, pytest, and
package-validation gates before merge. Runtime execution remains a later,
separately authorized transition.

## Commercial proof angle

This artifact is a direct proof asset for an AI Reliability Audit or Agent Harness
Hardening Sprint: it demonstrates how cache claims, route claims, request budgets,
runtime identity, failure evidence, and teardown are turned into machine-checkable
contracts instead of prompt-level assumptions.
