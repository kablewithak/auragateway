# Runbook: preflight-v3 exact-runtime resolution reconnaissance v1

## Purpose

Execute exactly one CPU-only Kaggle dependency-resolution reconnaissance after
the implementation PR is merged and the merged notebook identity is verified.

## Repository notebook

```text
notebooks/auragateway_preflight_v3_exact_runtime_resolution_reconnaissance_v1.ipynb
```

Requested Kaggle title:

```text
ag-preflight-v3-runtime-resolution-recon-v1
```

## Required Kaggle settings

```text
Accelerator: None
Internet: On
Secrets: None
Inputs: None
```

Do not attach the historical wheelhouse, model snapshot, benchmark dataset, or
any other Kaggle input. The notebook is dependency reconnaissance only.

## Prohibited actions

Do not:

- enable GPU;
- attach secrets;
- attach datasets;
- install packages interactively;
- edit the notebook in Kaggle;
- load Qwen;
- start vLLM workers;
- issue model requests;
- run benchmark trajectories;
- reuse the historical 0.19.1 resolution lock as the new lock;
- claim runtime qualification.

## Success output

The notebook must terminate with a JSON summary containing:

```text
status=COMPLETED_PENDING_REVIEW
exact_planned_vllm_sha256_matches_preflight_v3=true
torch_2_11_0_cu129_resolved=true
package_installation_performed=false
artifact_download_retention_permitted=false
retained_wheel_file_count=0
model_loads_performed=0
model_requests_performed=0
benchmark_trajectories_performed=0
credentials_used=false
customer_data_used=false
external_spend=0
qualification_claimed=false
exact_resolution_lock_frozen=false
save_this_notebook_output=true
```

Preserve the saved notebook output and the generated transport ZIP. Do not
convert the result into an exact lock until repository review confirms the
artifact inventory and host policy.

## Failure output

Any failure is terminal for this attempt. Preserve:

- Kaggle execution log;
- `resolution_failure.json` if emitted;
- saved notebook identity.

Do not patch the notebook in Kaggle. Return to the repository for evidence-led
debugging.

## Post-run next gate

If the evidence is accepted:

`freeze_preflight_v3_exact_runtime_resolution_lock_v1`

If it fails:

`classify_preflight_v3_exact_runtime_resolution_reconnaissance_failure_v1`
