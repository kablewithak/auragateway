# AuraGateway vLLM CUDA 12.8 wheelhouse materialization and verification

## Purpose

Produce one complete Python 3.12 CUDA 12.8 wheelhouse for vLLM `0.19.1+cu128` and validate it in a
fresh T4 x2 Kaggle environment without loading a model or issuing requests.

This is a two-notebook compatibility campaign. It is not an environment qualification attempt.

## Phase A: materializer

Notebook:

```text
ag-vllm-cu128-wheelhouse-materializer-v1
```

Settings:

```text
Accelerator: None
Internet: On
Secrets: None
Inputs: none
```

The notebook selects the exact official vLLM `0.19.1+cu128` x86_64 release asset, resolves the complete
Python 3.12 dependency closure, downloads wheels, and writes hash-locked acquisition and runtime files.

Run exactly once with:

```text
Save Version
→ Save & Run All
```

Required status:

```text
Version 1
Successful
```

Required saved output:

```text
auragateway_vllm_cu128_wheelhouse_v1/
├── wheels/
├── requirements.in
├── materialization.lock.txt
├── requirements.lock.txt
├── install_runtime.py
├── runtime_manifest.json
├── sha256_manifest.json
└── materialization_receipt.json
```

Required terminal fields:

```text
vllm_distribution=0.19.1+cu128
materialization_status=PASSED
model_requests_performed=0
qualification_claimed=false
save_this_notebook_output=true
```

Preserve Version 1. Do not edit or rerun a successful materialization.

## Phase B: offline compatibility verifier

Notebook:

```text
ag-vllm-cu128-offline-compatibility-v1
```

Settings:

```text
Accelerator: T4 x2
Internet: Off
Secrets: None
Inputs: exactly the Version 1 saved output from the materializer
```

Use native `Run All` exactly once because this is a focused diagnostic verifier, not governed
qualification evidence. Save the executed notebook afterward with:

```text
Save Version
→ Quick Save
```

Do not choose `Save & Run All` after the native run because that would execute it a second time.

Required artifact:

```text
/kaggle/working/ag-vllm-cu128-offline-compatibility-v1.zip
```

Required terminal fields:

```text
offline_compatibility_status=PASSED
failed_required_roles=[]
model_requests_performed=0
qualification_claimed=false
upload_only_this_file=true
```

The verifier must independently pass:

```text
offline isolated installation
pip check
two-T4 topology
Python 3.12
torch 2.10.0+cu128
CUDA 12.8
Transformers 5.5.3
vLLM distribution 0.19.1+cu128
vLLM module import
vLLM native-extension import
```

## Stop policy

Do not load the model, start vLLM workers, issue prompts, attach an authorization, or reuse this
diagnostic as qualification evidence. A failure is preserved with the verifier ZIP and Kaggle log
before any harness integration work begins.
