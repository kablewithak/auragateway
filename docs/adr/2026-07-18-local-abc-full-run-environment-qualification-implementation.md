# ADR: Implement static full-run environment-qualification tooling

- Status: accepted
- Date: 2026-07-18
- Decision ID: `auragateway-full-abc-local-environment-qualification-implementation-v1`
- Source main merge: `7be3361fbbfcd14cebee96b4832fe4c800702f2e`
- Source review blob: `344a24f18fc32a7b945ce761f6420947a53bcc24`

## Context

PR #101 approved implementation of typed tooling for a fresh full-run environment
qualification. It did not authorize a Kaggle session, GPU use, worker startup, model execution,
credential access, provider calls, qualification claims, manifest freeze, or measured execution.

The implementation stage is allowed to generate only two static assets:

- `qualification_request.json`
- `worker_startup_plan.json`

The eight runtime evidence artifacts remain reserved for a separate qualification-execution gate.

## Decision

Implement a schema-first static generator and verifier with these properties:

1. Bind the exact PR #101 review artifact and review-source Git blobs.
2. Generate a deterministic qualification request for the 342-trajectory lineage.
3. Generate a canonical two-worker startup plan without launching either worker.
4. Keep the developer dependency lock separate from the future Kaggle runtime lock.
5. Require all runtime versions and GPU facts to come from one fresh runtime session.
6. Represent unavailable cache metrics as `UNAVAILABLE_NOT_ZERO`.
7. Reject zero-filled missing metrics and latency-only cache inference.
8. Require full worker exit, closed-port verification, restart, and identity revalidation for reset.
9. Fail verification if any runtime evidence artifact exists before its authorized gate.
10. Preserve zero spend, no customer data, no credentials, and no hosted fallback.

## Worker startup plan

The static plan binds two non-shell, loopback-only vLLM commands:

- `worker_1`: GPU 0, port 8001
- `worker_2`: GPU 1, port 8002

Both commands bind the same model and tokenizer revisions, enable prefix caching, disable request
logging, and set `HF_HUB_OFFLINE=1`. Each command and environment payload has its own canonical
SHA-256 identity.

The plan does not assert that the commands are currently executable. Package versions, wheel
identity, GPU topology, model availability, and worker health remain fresh-capture requirements.

## Generated assets

```text
benchmarks/local_abc/
  auragateway_full_abc_local_full_run_environment_qualification_implementation_v1.json

data/evals/benchmark/environment-qualification-v1/
  qualification_request.json
  worker_startup_plan.json
```

## Deferred runtime evidence

The implementation deliberately does not generate:

```text
cache_metric_capability_report.json
gpu_topology_report.json
kaggle_runtime_dependency_lock.json
manifest.json
model_identity_report.json
qualification_report.json
reset_capability_report.json
worker_health_report.json
```

## Failure handling

Expected failures use metadata-safe error envelopes. The generator fails closed on:

- source review or Git ancestry drift;
- unsafe review mutations;
- static asset validation failures;
- noncanonical generated assets;
- startup topology or command drift;
- missing-metric zero fill;
- early runtime evidence generation; or
- implementation-plan drift.

No raw prompts, documents, credentials, environment secrets, or customer data are logged.

## Consequences

The repository now contains deterministic, reviewable preparation for a fresh qualification
session without implying that the environment is qualified. The next legal boundary is a review
of the qualification-execution procedure, evidence capture, stop conditions, and authorization.

## Next gate

`full_abc_local_full_run_environment_qualification_execution_review`

That review may authorize creation of an execution package. It may not itself claim that the
runtime has passed qualification or authorize the 342-trajectory measured benchmark.
