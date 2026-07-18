# Local A/B/C environment-qualification authorization package runbook

Status: static authorization-input package only.

The package prepares exact inputs for a later authorization-issuance review. It does not create
operational authorization and must not start Kaggle, attach datasets, install runtime packages,
enable GPUs, launch workers, invoke a model, or generate qualification evidence.

## Governing gate

Source review:

```text
full_abc_local_full_run_environment_qualification_execution_authorization_review
```

Current implementation gate:

```text
full_abc_local_full_run_environment_qualification_execution_authorization_implementation
```

Next gate:

```text
full_abc_local_full_run_environment_qualification_execution_authorization_issuance_review
```

The final authorization remains absent at:

```text
benchmarks/local_abc/
auragateway_full_abc_local_full_run_environment_qualification_
execution_authorization_v1.json
```

## Implemented package

This gate adds:

```text
src/auragateway/local_abc/
full_abc_local_environment_qualification_execution_authorization_contracts.py

src/auragateway/local_abc/
full_abc_local_environment_qualification_execution_authorization.py

src/auragateway/local_abc/
full_abc_local_environment_qualification_kaggle_runtime_adapter.py

tests/unit/local_abc/
test_full_abc_local_environment_qualification_execution_authorization.py

data/evals/benchmark/environment-qualification-v1/
qualification_authorization_request.json

data/evals/benchmark/environment-qualification-v1/
offline_dataset_manifest_request.json

docs/runbooks/
local_abc_full_run_environment_qualification_authorization_v1.md
```

## Static generation and verification

Run from the repository root:

```powershell
python -m auragateway.local_abc.full_abc_local_environment_qualification_execution_authorization generate `
    --repo-root .

python -m auragateway.local_abc.full_abc_local_environment_qualification_execution_authorization verify `
    --repo-root .
```

Expected state:

```text
authorization_package_generated=true
runtime_adapter_generated=true
runtime_adapter_executed=false
final_authorization_generated=false
materialized_dataset_manifest_generated=false
kaggle_session_started=false
gpu_execution_authorized=false
worker_started=false
model_execution_performed=false
runtime_evidence_generated=false
maximum_model_requests=8
benchmark_trajectory_requests_permitted=0
external_spend=0
```

## Two-layer dataset provenance

The existing execution harness consumes a compact runtime manifest containing:

```text
role
mounted_path
sha256
```

That shape is sufficient to verify mounted files during execution, but it does not retain the
Kaggle dataset slug or immutable dataset version required for issuance review.

Authorization therefore requires two hash-linked artifacts after dataset materialization.

### 1. Canonical materialization record

Future path:

```text
data/evals/benchmark/environment-qualification-v1/
offline_dataset_materialization_record.json
```

Each role must retain:

```text
role
kaggle_dataset_slug
kaggle_dataset_version
mounted_path
sha256
network_fallback_permitted=false
```

The record must also bind:

```text
harness_source_commit
runtime_manifest_path
runtime_manifest_sha256
network_access_permitted=false
credentials_present=false
customer_data_present=false
hosted_provider_inputs_present=false
```

### 2. Portable runtime manifest

Future path:

```text
data/evals/benchmark/environment-qualification-v1/offline_dataset_manifest.json
```

This is the exact projection consumed in Kaggle. Its three entries must preserve the same role,
mounted path, and SHA-256 values as the materialization record. The authorization tooling rejects
any projection drift or hash mismatch.

Mounted paths must remain under:

```text
/kaggle/input
```

## Exact offline roles

The materialization record must preserve this order:

```text
harness_source
model_artifacts
vllm_wheel
```

### `harness_source`

Required content:

- Source tree materialized from the post-implementation merge commit.
- The authorization contracts and runner.
- The concrete Kaggle runtime adapter.
- The existing qualification execution contracts and runner.
- The unexecuted qualification notebook.
- The frozen worker startup plan.

The source tree must not be built from PR #104 or PR #105 alone. It must bind the merge commit
that contains the current bootstrap, runner, adapter, and authorization implementation. The final
Kaggle dataset must expose the repository root directly, including `src/auragateway`, rather than
requiring an unverified pre-import extraction step.

### `model_artifacts`

Required content:

- Offline Hugging Face cache layout for `Qwen/Qwen2.5-0.5B-Instruct`.
- Exact model revision:
  `7ae557604adf67be50417f59c2c2f167def9a775`.
- Exact tokenizer revision:
  `7ae557604adf67be50417f59c2c2f167def9a775`.
- `config.json`.
- `tokenizer_config.json`.
- `tokenizer.json`.

The adapter accepts the exact expanded Hugging Face snapshot directory mounted by Kaggle. It
also retains archive compatibility for `.tar.gz`, `.tgz`, and `.zip` inputs used by local tests and
historical materialization flows. Directory inputs must preserve the exact `hf_home/hub/.../snapshots`
layout. The adapter copies the mounted read-only snapshot into a bounded writable workspace before
worker startup. Directory inputs reject symlinks and non-regular members. Archive inputs also
reject hard links, path traversal, and encrypted ZIP members. All inputs remain bounded by the
copy or extraction budget.

### `vllm_wheel`

Required content:

- Exact local vLLM `0.25.1` wheel.
- SHA-256 captured after upload and before authorization issuance.

The adapter installs only from the mounted wheel using:

```text
python -m pip install --no-index --no-deps <mounted-wheel>
```

No package index or network fallback is permitted.

## Concrete runtime adapter

Factory binding:

```text
auragateway.local_abc.
full_abc_local_environment_qualification_kaggle_runtime_adapter:
create_runtime_adapter
```

The adapter implements the existing typed `QualificationRuntimeAdapter` protocol and returns one
complete in-memory `QualificationRuntimeCapture`.

The existing execution harness remains the only owner of transactional evidence commit.

The adapter must never write partial evidence directly.

## Frozen worker topology

The adapter accepts only the exact startup-plan identities:

```text
worker_1 -> GPU 0 -> 127.0.0.1:8001
worker_2 -> GPU 1 -> 127.0.0.1:8002
```

It binds the complete argv, environment, and command SHA-256 for each worker.

Required worker controls include:

```text
--enable-prefix-caching
--disable-log-requests
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
CUDA_VISIBLE_DEVICES=<bound GPU>
```

Shell execution, alternate ports, alternate GPUs, non-loopback hosts, extra model retries, and
startup-command drift fail before qualification proceeds.

## Qualification sequence

After a separately merged and still-valid final authorization exists, the adapter is expected to:

1. Reject credential-bearing environment variables and customer-data flags.
2. Validate all three mounted inputs against the authorized runtime manifest.
3. Extract the exact model cache through the bounded archive boundary.
4. Install the exact local vLLM wheel without network access or dependency resolution.
5. Capture two Tesla T4 devices at indexes 0 and 1.
6. Capture Python, CUDA, Torch, Transformers, vLLM, wheel, model, tokenizer, and startup identities.
7. Start both frozen loopback workers without a shell.
8. Poll only the worker health endpoints through a bounded readiness loop.
9. Validate the served model identity on each worker.
10. Run four cold/warm synthetic probes without model-request retries.
11. Stop both workers and prove processes exited and ports 8001 and 8002 closed.
12. Restart both exact worker plans.
13. Revalidate model, tokenizer, worker, route, health, and metric baselines.
14. Run two post-reset synthetic probes.
15. Stop both workers.
16. Return one complete in-memory evidence capture.
17. Allow the existing execution harness to validate and atomically commit all eight artifacts.

A partial worker start is cleaned up before the adapter returns an error.

## Metric capability boundary

The adapter reads Prometheus-compatible metrics only from each loopback worker's `/metrics`
endpoint.

The required token and request semantics are bound to explicit raw metric names. No value may be
inferred from latency alone, and a missing metric cannot be converted to zero.

Required semantic set:

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

The adapter accepts only nonnegative per-request deltas. Counter regression, missing source
metrics, or source-name drift fails qualification.

The metric capability report still does not claim that the final A/B/C experiment achieved a
cache benefit. It establishes only that the runtime exposes the evidence needed to evaluate that
claim later.

## Reset boundary

The required reset sequence remains:

```text
confirm_worker_process_exit
confirm_worker_ports_closed
record_reset_start
restart_workers_from_bound_startup_plan
revalidate_model_tokenizer_and_worker_identity
verify_fresh_health_and_metric_baseline
```

Namespace-only reset is not accepted. The full worker process restart is mandatory.

## Materialization procedure after this PR merges

Do not perform this procedure from the feature branch.

1. Merge the authorization implementation PR.
2. Sync clean `main` and record the full merge commit.
3. Materialize the tracked `harness_source` tree from that exact commit.
4. Calculate its canonical sorted file-manifest SHA-256.
5. Attach and inspect the exact expanded model snapshot directory.
6. Calculate its canonical sorted file-manifest SHA-256.
7. Verify the exact vLLM wheel and calculate its SHA-256.
8. Upload or version all three Kaggle datasets.
9. Record each exact Kaggle slug and immutable dataset version.
10. Record each exact `/kaggle/input/...` mounted path.
11. Ensure the final authorization and portable runtime manifest will also be supplied as
    immutable `/kaggle/input` files for the notebook bootstrap; they are control artifacts, not
    additional qualification dataset roles.
12. Construct the canonical materialization record.
13. Project the portable runtime manifest from that record.
14. Bind the runtime manifest fingerprint back into the materialization record.
15. Validate both artifacts with the authorization tooling.
16. Open the separate authorization-issuance review.

## Issuance-input inspection

After both future files exist, run:

```powershell
python -m auragateway.local_abc.full_abc_local_environment_qualification_execution_authorization inspect-issuance-inputs `
    --repo-root . `
    --materialization-record `
        data/evals/benchmark/environment-qualification-v1/offline_dataset_materialization_record.json `
    --runtime-manifest `
        data/evals/benchmark/environment-qualification-v1/offline_dataset_manifest.json
```

The command validates:

- Exact role order.
- Exact Kaggle slug and version presence.
- Exact mounted-path and SHA-256 projection.
- Runtime-manifest hash linkage.
- Harness-source commit ancestry.
- Concrete adapter existence.
- Static adapter safety constraints.
- Concrete adapter SHA-256.
- Absence of final authorization generation.

## Issuance review requirements

The later issuance review must bind:

```text
qualification execution request SHA-256
offline dataset request SHA-256
materialization record SHA-256
portable runtime manifest SHA-256
runtime adapter SHA-256
runtime factory module:function
harness source merge commit
PR #105 review authority
operator confirmation
timezone-aware issuance and expiry
maximum authorization window=240 minutes
maximum Kaggle sessions=1
maximum workers=2
maximum model requests=8
maximum output tokens per request=32
benchmark trajectory requests permitted=0
external spend=0
```

The issuance review must inspect the exact uploaded artifacts. It cannot approve placeholders,
mutable `latest` references, incomplete manifests, or hashes calculated before upload.

## Hard stops

Stop without retry or downgrade on:

- Missing or invalid final authorization.
- Authorization outside its validity window.
- Materialization-record drift.
- Runtime-manifest drift.
- Harness-source commit mismatch.
- Adapter SHA-256 mismatch.
- Dataset SHA-256 mismatch.
- Credential or customer-data presence.
- Network fallback.
- Unexpected GPU topology.
- Worker argv, environment, topology, or command-identity drift.
- Worker readiness failure.
- Model or tokenizer identity mismatch.
- Required metric unavailability.
- Metric counter regression.
- Reset sequence failure.
- Route realization mismatch.
- Model request budget exhaustion.
- Any nonzero external spend.

## Current non-claims

This implementation does not claim:

- Kaggle datasets have been materialized.
- The concrete adapter has run in Kaggle.
- vLLM `0.25.1` is compatible with the future Kaggle image.
- The expected metrics are available in the future runtime.
- The model and tokenizer load successfully.
- Two T4 devices are currently available.
- Worker health has been established.
- Cache reuse has occurred.
- Reset correctness has been established in a live runtime.
- The environment is qualified.
- The 342-trajectory benchmark is authorized.
- Measured execution is ready.
- AuraGateway is production-ready.
