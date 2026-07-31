# AuraGateway CUDA 12.9 P3-P6 Runtime Diagnostic V1

## Executive result

A repository-only implementation candidate has been prepared against main
`58a73c38c22337219899018d655e00366d790413`. It is bound to the accepted Q6 execution and the Option C
runtime-diagnostic decision.

Status:

`IMPLEMENTED_NOT_EXECUTED`

## Why a new diagnostic surface is required

The historical qualification adapter is valuable for its helpers and typed
contracts, but its control flow starts two workers before P3 is isolated. It
also proves metric availability rather than the causal cache relationship
required by P5.

The new diagnostic therefore reuses stable seams without reusing the
monolithic capture sequence.

## Probe contracts

### P3

Start worker 1 only:

- GPU 0
- port 8001
- explicit `TRITON_ATTN`
- Internet off
- fixed model and tokenizer revision
- bounded health polling
- exact `/v1/models` identity
- bounded backend startup-marker polling

Pass decision:

`ONE_WORKER_TRITON_STARTUP_PASSED`

### P4

Issue one deterministic synthetic chat request:

- temperature 0
- top-p 1
- seed 7
- maximum 32 output tokens
- no raw prompt or output logging
- valid JSON object equal to the requested synthetic object
- valid response structure and usage metadata

Pass decision:

`ONE_REQUEST_RUNTIME_COMPATIBILITY_PASSED`

### P5

Use worker 1 for:

1. cold request;
2. warm request with the same long prefix;
3. full worker-process shutdown;
4. closed-port verification;
5. worker restart with a new PID;
6. post-reset baseline request.

Pass requires positive warm cached tokens, reduced warm prefill computation,
zero post-reset cached tokens, and positive post-reset recomputation.

Pass decision:

`CACHE_SMOKE_AND_RESET_PASSED`

### P6

Start worker 2 only after P5:

- GPU 1
- port 8002
- distinct process tree
- GPU process attribution through `nvidia-smi`
- worker-specific route and metric deltas
- no cross-worker prompt-token counter movement

Pass decision:

`DUAL_WORKER_DIAGNOSTIC_PASSED`

## Generated artifacts

- typed request
- typed architecture review
- readable Python template
- deterministic unexecuted Kaggle notebook
- typed implementation record
- focused regression tests
- ADR
- engineering report
- runbook

Notebook:

`ag-cu129-p3-p6-runtime-diagnostic-v1`

Failed lineage name:

`ag-cu129-p3-p6-runtime-diag-failed-v1`

Evidence ZIP:

`ag-cu129-p3-p6-runtime-evidence-v1.zip`

## Validation completed in the delivery fixture

- deterministic generation: passed
- fresh semantic validation: passed
- generated notebook compilation: passed
- Python line bound: passed
- focused tests: 17 passed
- exact structured-output contract: passed
- pre-side-effect action-budget guards: passed
- machine-readable failure taxonomy: passed
- deterministic pass/fail evidence member set: passed
- authority tamper rejection: passed
- generated drift rejection: passed
- runtime authorization absence: passed

## Safety state

No Kaggle execution, GPU action, runtime installation, model load, worker
start, request, benchmark trajectory, credential access, customer-data
processing, or external spend occurred while preparing this candidate.

## Commercial proof angle

This tranche demonstrates harness hardening rather than a model demo. A CTO can
inspect the exact runtime contract, failure taxonomy, action budget, evidence
lineage, partial-failure handling, privacy boundary, and next authorization
gate before spending another GPU session.

## Non-claims

The implementation has not been executed on Kaggle. Runtime success, cache
success, dual-worker readiness, deployment, and production readiness remain
unproven.
