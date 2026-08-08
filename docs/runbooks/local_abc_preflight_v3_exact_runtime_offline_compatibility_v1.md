# Runbook: preflight-v3 exact-runtime offline compatibility verifier V1

## Repository notebook

```text
notebooks/auragateway_preflight_v3_exact_runtime_offline_compatibility_v1.ipynb
```

Requested Kaggle title:

```text
ag-preflight-v3-runtime-offline-verifier-v1
```

## Settings

```text
Accelerator: T4 x2
Internet: Off
Secrets: None
Inputs: exactly one input, the saved output of materializer scriptVersionId 341083505
```

Do not attach the model snapshot, benchmark harness, qualification
authorization, historical 176-wheel wheelhouse, or customer data.

## Input requirement

The attached saved materializer output must contain exactly one directory named:

```text
auragateway_preflight_v3_exact_runtime_wheelhouse_v1
```

The verifier recursively locates that directory beneath `/kaggle/input`, then
fails closed unless its internal topology and hashes match the accepted
materialization.

## Execution

After the implementation PR is merged and post-merge closure passes:

```text
Save Version
→ Save & Run All
```

Run exactly once. Preserve Version 1 whether the technical result passes or
fails.

## Expected PASS terminal state

```text
offline_compatibility_status=PASSED_PENDING_REPOSITORY_ACCEPTANCE
failed_required_roles=[]
locked_package_count=196
validated_manifest_entry_count=200
total_wheel_bytes=6164913809
package_installation_started=true
package_installation_performed=true
dependency_resolution_performed=false
internet_required=false
model_loads_performed=0
model_requests_performed=0
worker_startups_performed=0
benchmark_trajectories_performed=0
qualification_claimed=false
exact_runtime_offline_verified=false
runtime_execution_authorized=false
pilot_execution_authorized=false
final_measured_abc_execution_authorized=false
```

The verifier intentionally keeps `exact_runtime_offline_verified=false` until
the saved execution is reviewed and accepted back into repository authority.

## Failure policy

A technical failure is admissible diagnostic evidence.

Do not edit or rerun the notebook to force a pass. Preserve Version 1 and
upload:

1. the verifier evidence ZIP;
2. the complete execution log;
3. the saved executed notebook;
4. the Kaggle URL/scriptVersionId.

## Stop policy

After the verifier finishes, turn both GPUs off. Do not load a model, start
vLLM workers, issue requests, or run P5/P6.
