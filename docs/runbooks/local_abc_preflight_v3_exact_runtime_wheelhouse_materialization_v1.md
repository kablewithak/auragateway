# Runbook: preflight-v3 exact-runtime wheelhouse materializer v1

## Repository notebook

```text
notebooks/auragateway_preflight_v3_exact_runtime_wheelhouse_materialization_v1.ipynb
```

Requested Kaggle title:

```text
ag-preflight-v3-runtime-materializer-v1
```

## Kaggle settings

```text
Accelerator: None
Internet: On
Secrets: None
Inputs: None
```

Do not attach the reconnaissance output, historical wheelhouse, model snapshot, benchmark data, or
any customer data. The exact resolution lock is embedded and hash-bound in the committed notebook.

## Execution contract

Run exactly once with:

```text
Save Version
→ Save & Run All
```

Do not edit the notebook in Kaggle.

The notebook must:

- decode and verify lock SHA `1294394ac476336b103b036d8654a49e4ae78c25c912ca5729cd94f982384f3c`;
- download exactly 196 locked wheels;
- perform no dependency resolution;
- perform no package installation;
- verify every wheel SHA-256;
- reject missing or extra wheel filenames;
- preserve the five-host artifact-authority boundary;
- permit only the one-hop GitHub release transport redirect to
  `release-assets.githubusercontent.com`;
- emit a 200-entry SHA manifest covering 196 wheels and four governed control files;
- emit a materialization receipt;
- emit `materialization_evidence.zip`.

## Successful terminal state

```text
materialization_status=PASSED_PENDING_REPOSITORY_ACCEPTANCE
locked_package_count=196
downloaded_package_count=196
wheel_file_count=196
authority_host_count=5
dependency_resolution_performed=false
package_installation_performed=false
model_loads_performed=0
model_requests_performed=0
benchmark_trajectories_performed=0
credentials_used=false
customer_data_used=false
external_spend=0
wheelhouse_materialized=true
exact_runtime_materialized=false
exact_runtime_offline_verified=false
qualification_claimed=false
upload_only_this_file=materialization_evidence.zip
save_this_notebook_output=true
```

## Failure policy

Any failure is terminal for the saved version. Preserve the version and execution log. Do not edit
and rerun to force a pass.

## After execution

Upload only:

1. `materialization_evidence.zip`;
2. complete execution log;
3. saved executed `.ipynb`.

Do not upload the multi-gigabyte wheelhouse into chat.

The saved Kaggle version itself becomes the candidate input for the later offline T4x2 verifier only
after repository acceptance.

## Non-claims

This run does not perform offline installation, vLLM import qualification, P5/P6 requalification,
variance-pilot execution, or final measured A/B/C execution.
