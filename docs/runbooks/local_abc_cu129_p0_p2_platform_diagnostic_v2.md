# Runbook: CUDA 12.9 P0-P2 platform diagnostic V2

## Repository boundary

```text
source main:
fe297a6f1aeed04119452552874dab22bfe01dee

notebook:
notebooks/auragateway_cu129_p0_p2_platform_diagnostic_v2.ipynb

Kaggle name:
ag-cu129-p0-p2-platform-diagnostic-v2

failed lineage name:
ag-cu129-p0-p2-platform-diag-failed-v2
```

Both Kaggle names are below 50 characters.

## Required Kaggle configuration

```text
Accelerator: T4 x2
Internet: Off
Secrets: none
Inputs: exactly one
```

Attach saved Version 1 output from:

```text
auragateway-cu129-wheelhouse-materializer-v1
```

The attached output must contain exactly one directory named:

```text
auragateway_vllm_cu129_wheelhouse_v1
```

Do not attach a model, source materializer, previous diagnostic output or any
other Dataset.

## Execution

After the implementation PR is merged and main is synchronized:

```text
Save Version
-> Save & Run All
```

Execute exactly one saved version. Do not manually run cells first.

## Success

```text
terminal_decision=P0_P2_PLATFORM_DIAGNOSTIC_V2_PASSED
next_gate=implement_explicit_triton_attention_backend
```

## Failure

Preserve:

```text
complete execution log
ag-cu129-p0-p2-platform-evidence-v2.zip
saved-version URL
```

Rename the failed notebook lineage:

```text
ag-cu129-p0-p2-platform-diag-failed-v2
```

Do not rerun an unchanged failed version.

## Required evidence ZIP members

```text
platform_identity_report_v2.json
explicit_cuda_driver_link_report_v2.json
minimal_triton_kernel_report_v2.json
p0_p2_platform_diagnostic_summary_v2.json
bundle_manifest_v2.json
human_report_v2.md
```

## Prohibitions

- no GitHub CLI;
- no Kaggle CLI;
- no Internet;
- no global linker-environment mutation;
- no CUDA toolkit stub;
- no libcuda copy or symlink;
- no vLLM import;
- no model;
- no worker;
- no model request;
- no benchmark trajectory;
- no hidden retry.

## Next gate after merge

`EXECUTE_GOVERNED_P0_P2_PLATFORM_DIAGNOSTIC_V2`
