# Worker-observability CUDA 12.9 harness evidence integration runbook

## Immutable Kaggle authority

```text
materializer notebook: ag-worker-obs-harness-materializer-v1
materializer saved version: 337284215
materializer URL: https://www.kaggle.com/code/kabomolefe/ag-worker-obs-harness-materializer-v1/notebook?scriptVersionId=337284215
inspection notebook: ag-worker-obs-input-inspection-v1
inspection saved version: 337286728
inspection URL: https://www.kaggle.com/code/kabomolefe/ag-worker-obs-input-inspection-v1/notebook?scriptVersionId=337286728
```

## Current harness authority

```text
source commit: dceda98989386de7a4d57616f9f8a8023f866f10
mounted path: /kaggle/input/notebooks/kabomolefe/ag-worker-obs-harness-materializer-v1/ag_worker_obs_harness_materializer_v1_output/auragateway_qualification_harness_dceda98_worker_obs_v1
directory SHA-256: c66f2589bdf55ab34f82bffc1eaaa4b4c7e73cb8195867333ccd99a58438f3e4
file count: 1076
total bytes: 10850278
materialization receipt SHA-256: 5f2818130abcf338239f49f38683fbdb00c2a290816115925e74e508ea9d0f02
inspection evidence ZIP SHA-256: e1bf87f44c3ccbf3eda65938cb61b833c95edfb7c200e5f40095eab9e3f936fb
```

## Repository integration

The integration PR must keep all external evidence immutable, update the active manifest and materialization record, regenerate the launcher notebook from source, and validate source-to-harness-to-launcher parity.

The historical `426f57d` evidence remains immutable. It is no longer the active harness authority and must not be relabeled as containing worker-startup observability.

## Validation command

```powershell
python -m auragateway.local_abc.cu129_worker_observability_harness_integration --repo-root .
```

Expected terminal state:

```text
status=WORKER_OBSERVABILITY_HARNESS_EVIDENCE_INTEGRATED
operational_input_closure=PASSED
source_commit=dceda98989386de7a4d57616f9f8a8023f866f10
harness_directory_sha256=c66f2589bdf55ab34f82bffc1eaaa4b4c7e73cb8195867333ccd99a58438f3e4
active_manifest_promoted=true
historical_issuer_usable=false
authorization_issued=false
gpu_execution_performed=false
model_requests_performed=0
next_gate=fresh_cu129_authorization_issuance_implementation
```

## Stop conditions

Stop immediately if any evidence hash drifts, the saved version IDs differ, the active manifest points at a historical harness, launcher generation is not deterministic, runtime/model authority changes, or a transient authorization exists.

## Non-execution boundary

```text
authorization_issued=false
gpu_execution_performed=false
package_installation_performed=false
model_loaded=false
worker_started=false
model_requests_performed=0
```
