# Runbook: preflight-v3 exact-runtime offline compatibility V2

## Purpose

Execute the smallest governed successor to the V1 false-negative diagnostic.

## Immutable V1

```text
scriptVersionId=341091805
```

Do not rerun or edit V1.

## V2 Kaggle settings

```text
Notebook:
auragateway_preflight_v3_exact_runtime_offline_compatibility_v2.ipynb

Title:
ag-preflight-v3-runtime-offline-verifier-v2

Accelerator:
T4 x2

Internet:
Off

Secrets:
None

Inputs:
exactly the saved output of materializer scriptVersionId=341083505
```

## V2 expected difference

The exact distribution gate remains `0.25.1+cu129`.

The module gate expects `vllm.__version__ == 0.25.1`.

If the module gate passes, V2 must proceed to the previously blocked
`vllm._C` native-extension import.

## Failure policy

Save and preserve V2 Version 1 whether PASS or FAIL. Do not edit/rerun to force
a pass.

Upload after execution:

1. evidence ZIP;
2. complete execution log;
3. saved executed notebook;
4. Kaggle URL/scriptVersionId.

Turn both GPUs off after the run.

## Authorization state

V2 does not authorize model loading, worker startup, requests, P5/P6,
variance-pilot execution, or final measured A/B/C.
