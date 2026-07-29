# Runbook: CUDA 12.9 P0-P2 Execution Launcher V2

## Purpose

Execute the exact reviewed P0-P2 platform diagnostic once through a dedicated
launcher. This runbook starts only after the launcher implementation PR merges.

## Resource names

```text
launcher notebook:
ag-cu129-p0-p2-execution-launcher-v2

failed lineage:
ag-cu129-p0-p2-exec-failed-v2

launcher evidence ZIP:
ag-cu129-p0-p2-execution-launcher-v2.zip
```

All names are below Kaggle's 50-character limit.

## Inputs

Attach exactly two successful notebook outputs:

1. `ag-cu129-p0-p2-source-materializer-v2`, accepted version `338895141`;
2. the existing governed CUDA 12.9 wheelhouse output containing exactly one
   `auragateway_vllm_cu129_wheelhouse_v1` directory.

Do not create or attach a standalone `ag-cu129-p0-p2-source-v2` Dataset. Do not
attach a model snapshot, authorization package, control materializer, customer
data, or secrets.

## Kaggle settings

```text
Notebook name: ag-cu129-p0-p2-execution-launcher-v2
Accelerator: T4 x2
Internet: Off
Secrets: none
Save Version -> Save & Run All: exactly once
```

## Hard action budget

```text
diagnostic executions <= 1
runtime installation attempts <= 1
minimal Triton compile-and-execution attempts <= 1
hidden retries = 0
model loads = 0
worker starts = 0
model requests = 0
benchmark trajectory requests = 0
network requests = 0
external spend = 0
```

## Success output

The launcher prints:

```text
status=P0_P2_EXECUTION_LAUNCHER_COMPLETED_V2
terminal_decision=<one governed terminal decision>
diagnostic_execution_attempts=1
```

It produces:

```text
p0_p2_execution_launcher_report_v2.json
ag-cu129-p0-p2-execution-launcher-v2.zip
ag_cu129_p0_p2_platform_diagnostic_v1/
ag-cu129-p0-p2-platform-evidence-v1.zip
```

The terminal decision is one of:

```text
P0_P2_PLATFORM_DIAGNOSTIC_PASSED
DIAGNOSTIC_INVALID
CURRENT_KAGGLE_IMAGE_LINKER_CONTRACT_FAILED
CURRENT_STACK_TRITON_INCOMPATIBLE
```

A passed platform diagnostic advances to
`implement_explicit_triton_attention_backend`. Any fail-closed platform result
advances to `preserve_evidence_and_classify_platform_failure`.

## Failure lineage

If the launcher fails unexpectedly, preserve its report, evidence ZIP, log, and
results. Rename that Kaggle notebook to
`ag-cu129-p0-p2-exec-failed-v2`. Do not rerun the failed lineage unchanged.

## Non-authorization

This run does not authorize model loading, vLLM worker startup, inference,
benchmark trajectories, full A/B/C qualification, or customer-data processing.
