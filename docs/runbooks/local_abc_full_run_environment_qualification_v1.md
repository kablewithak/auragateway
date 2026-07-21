# Local A/B/C full-run environment qualification runbook

Status: static package only. Execution is blocked until the separate
`full_abc_local_full_run_environment_qualification_execution_authorization_review` gate
merges an exact authorization artifact.

## Purpose

This runbook governs one offline Kaggle T4 x2 qualification session for the clean
342-trajectory AuraGateway A/B/C lineage. The qualification session validates the runtime
environment only. It must not execute benchmark trajectories, customer payloads, provider
calls, or measured A/B/C comparisons.

## Hard stop before authorization

Do not start Kaggle, attach datasets, install packages, enable GPUs, launch workers, or invoke
the model unless all of the following exist and match the static request:

1. The merged authorization artifact at the exact request-bound path.
2. An exact offline dataset manifest covering `harness_source`, `model_artifacts`, and
   `vllm_runtime`.
3. A runtime adapter artifact whose SHA-256 and `module:function` factory binding are frozen
   in the authorization.
4. A current authorization window that binds the request SHA-256, dataset manifest SHA-256,
   runtime adapter SHA-256, one Kaggle session, eight requests, and zero benchmark requests.

The repository intentionally contains none of those operational authorities in this slice.

## Static package validation

Run locally before creating any authorization review:

```powershell
python -m auragateway.local_abc.full_abc_local_environment_qualification_execution generate `
    --repo-root .

python -m auragateway.local_abc.full_abc_local_environment_qualification_execution verify `
    --repo-root .
```

Expected state:

```text
execution_package_generated=true
runtime_evidence_generated=false
execution_authorized=false
maximum_model_requests=8
benchmark_trajectory_requests_permitted=0
external_spend=0
```

## Approved offline inputs

The future authorization must bind exactly three mounted inputs:

| Role | Required content | Required identity |
|---|---|---|
| `harness_source` | Exact AuraGateway source tree plus runtime adapter | Tree SHA-256 |
| `model_artifacts` | Local Qwen model and tokenizer revision | SHA-256 manifest |
| `vllm_runtime` | Exact 176-package CUDA 12.9 wheelhouse | Control hashes and manifest |

Network fallback, credentials, hosted providers, customer data, raw prompt logging, and
network package installation are prohibited.


## Active CUDA 12.9 runtime contract

The qualification adapter must discover exactly one
`auragateway_vllm_cu129_wheelhouse_v1` directory beneath `/kaggle/input`. It validates
the exact resolution lock, runtime manifest, checksum manifest, materialization receipt,
176-wheel closure, and 5,727,339,111-byte wheel total before installation.

Installation and execution policies are fixed:

```text
BASE_PIP_TARGET_DIRECTORY
CONTROLLED_TARGET_METADATA_AND_PACKAGING
NO_SITE_WITH_CONTROLLED_SITE_BOOTSTRAP
TARGET_NVIDIA_LIBRARIES_PREPENDED
```

The Kaggle base interpreter remains unchanged. Workers start from the isolated target
interpreter with offline mode, no user site, target-first NVIDIA libraries, loopback-only
transport, prefix caching enabled, and request logging disabled.

## Probe budget

Only six fixed public-safe synthetic probes are permitted:

1. `worker-1-cold-prefix`
2. `worker-1-warm-prefix`
3. `worker-2-cold-prefix`
4. `worker-2-warm-prefix`
5. `worker-1-post-reset-baseline`
6. `worker-2-post-reset-baseline`

The hard budget is one Kaggle session, two workers, eight model requests, and 32 output tokens
per request. Hidden retries are prohibited. The two unused request slots are contingency
capacity only and may be consumed only by an authorization amendment; the default runner
requires exactly six successful probes for qualification.

## Required runtime sequence

1. Validate authorization, request, dataset manifest, runtime adapter, and current time.
2. Confirm network access is disabled and no credentials or customer data are present.
3. Validate the exact CUDA 12.9 wheelhouse, install it through base pip `--target`, and
   capture the controlled target-runtime dependency lock.
4. Capture GPU topology and require two Tesla T4 devices at indexes 0 and 1.
5. Validate model and tokenizer identity before worker startup.
6. Start exactly two loopback workers from the frozen startup plan.
7. Capture worker health, model identity, tokenizer identity, and route identity.
8. Run cold and warm synthetic probes on each worker without retries.
9. Capture raw runtime metrics and map every required semantic explicitly.
10. Stop both workers, prove process exit, and prove ports 8001 and 8002 are closed.
11. Record reset start, restart from the bound startup plan, and revalidate identity.
12. Run one post-reset baseline probe on each worker.
13. Stop workers and validate the complete in-memory evidence bundle.
14. Atomically write all eight evidence artifacts only after every contract passes.

## Metric requirements

The following semantics must all be available with explicit raw names and units:

```text
cached_prefix_tokens
metric_availability_state
newly_computed_prefill_tokens
prefill_duration_ms
prompt_tokens
realized_route
request_latency_ms
reset_state
time_to_first_token_ms
worker_id
```

Unavailable evidence remains `UNAVAILABLE_NOT_ZERO`. Zero filling and latency-only cache
inference are prohibited. Environment qualification requires every semantic to be available;
this gate still does not claim successful cache reuse.

## Evidence commit rule

The runner stages the seven non-manifest artifacts in memory, validates shared runtime-session,
request, dataset, privacy, spend, budget, reset, metric, and qualification invariants, builds the
manifest, then atomically commits all eight files. Any validation or write failure must leave no
partial evidence bundle.

## Notebook execution

Before importing any AuraGateway code, the notebook uses only the Python standard library to:

1. Require the authorization and dataset-manifest paths to remain under `/kaggle/input`.
2. Verify that authorization binds the fixed execution-request fingerprint.
3. Verify that authorization binds the canonical dataset-manifest fingerprint.
4. Verify the authorization window and fail-closed safety budget.
5. Verify the mounted `harness_source` tree against the manifest.
6. Copy the verified read-only source tree to
   `/kaggle/working/auragateway_qualification_harness` and rehash the copy.
7. Require the authorization to bind the runtime adapter by one bounded repository-relative path, then verify its SHA-256 inside that writable copy.
8. Add the verified copied `src` directory to `sys.path` and set `AURAGATEWAY_REPO_ROOT`.

Only after those checks does the notebook import the typed runner. The writable copy is required
because the runner transactionally commits the eight qualification evidence files beneath the
repository root. This prevents execution of unverified mounted source, writes to `/kaggle/input`,
or an authorization/manifest pair that drifted together.

The notebook requires these path bindings:

```text
AURAGATEWAY_QUALIFICATION_AUTHORIZATION
AURAGATEWAY_QUALIFICATION_DATASET_MANIFEST
```

The authorization itself binds the exact runtime adapter artifact and factory. Missing or
drifting bindings fail closed before the adapter is loaded.

## Stop conditions

Stop without retry on authorization, dataset, adapter, model, tokenizer, GPU, worker, route,
metric, reset, privacy, network, request-budget, spend, or evidence-lineage divergence. Do not
convert failures into zero-valued telemetry or partial qualification claims.

## Outputs

A successful authorized session writes exactly:

```text
data/evals/benchmark/environment-qualification-v1/cache_metric_capability_report.json
data/evals/benchmark/environment-qualification-v1/gpu_topology_report.json
data/evals/benchmark/environment-qualification-v1/kaggle_runtime_dependency_lock.json
data/evals/benchmark/environment-qualification-v1/manifest.json
data/evals/benchmark/environment-qualification-v1/model_identity_report.json
data/evals/benchmark/environment-qualification-v1/qualification_report.json
data/evals/benchmark/environment-qualification-v1/reset_capability_report.json
data/evals/benchmark/environment-qualification-v1/worker_health_report.json
```

A successful environment qualification does not freeze the benchmark execution manifest and
does not authorize the 342-trajectory measured run.
