# AuraGateway vLLM CUDA 12.9 wheelhouse materialization and verification

## Purpose

Produce one complete Python 3.12 CUDA 12.9 wheelhouse for the official vLLM `0.19.1` release and
validate it in a fresh T4 x2 Kaggle environment without loading a model or issuing requests.

This supersedes the failed cu128 asset-selection campaign. It is not environment qualification.

## Preserved failed attempt

```text
historical_notebook_title=auragateway-cu128-wheelhouse-asset-mismatch-v1
execution_log_sha256=b45bee3fd286f35d367ee25639100eb33b9244251d5a921dedd84c998e785a2d
failure_code=VLLM_CU128_RELEASE_ASSET_ABSENT
wheel_downloads_performed=0
model_requests_performed=0
qualification_claimed=false
```

Do not rerun that notebook.

## Phase A: materializer

Repository notebook:

```text
notebooks/auragateway_vllm_cu129_wheelhouse_materialization_v1.ipynb
```

Requested Kaggle title:

```text
auragateway-cu129-wheelhouse-materializer-v1
```

This title is within Kaggle's observed 50-character limit. Record the actual platform-assigned slug
after Version 1 is saved.

Settings:

```text
Accelerator: None
Internet: On
Secrets: None
Inputs: none
```

The notebook binds this exact official release asset:

```text
vllm-0.19.1-cp38-abi3-manylinux_2_31_x86_64.whl
sha256=71a87f46cafab4489c69a5c5c83b870d0235e5694d8222303d460576293dc719
```

It resolves the full CUDA 12.9 dependency closure, downloads binary wheels, and writes hash-locked
acquisition and runtime files.

Run exactly once with:

```text
Save Version
→ Save & Run All
```

Required saved output:

```text
auragateway_vllm_cu129_wheelhouse_v1/
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
vllm_distribution=0.19.1
materialization_status=PASSED
model_requests_performed=0
qualification_claimed=false
save_this_notebook_output=true
```

Preserve Version 1, download the output and execution log, record the actual slug, close the session,
and stop before the verifier.

## Phase B: offline compatibility verifier

Repository notebook:

```text
notebooks/auragateway_vllm_cu129_offline_runtime_compatibility_v1.ipynb
```

Requested Kaggle title:

```text
auragateway-cu129-offline-verifier-v1
```

Settings:

```text
Accelerator: T4 x2
Internet: Off
Secrets: None
Inputs: exactly the successful Version 1 materializer output
```

Do not attach the model snapshot, harness, authorization, control output, or rejected wheels.

Required evidence root:

```text
/kaggle/working/auragateway_vllm_cu129_offline_compatibility_evidence_v1/
```

Required artifact:

```text
/kaggle/working/auragateway_vllm_cu129_offline_compatibility_evidence_v1.zip
```

The verifier must independently pass:

```text
offline isolated installation
pip check
two-T4 topology
Python 3.12
torch 2.10.0+cu129
CUDA 12.9
Transformers 5.5.3
vLLM distribution 0.19.1
vLLM module import
vLLM native-extension import
```

## Stop policy

Do not load the model, start workers, issue prompts, create an authorization, run qualification, or make
cache, latency, quality, cost, or production-readiness claims.

## Preserved failed materializer attempts

### Attempt 1: explicit cu128 asset absent

```text
code=VLLM_CU128_RELEASE_ASSET_ABSENT
execution_log_sha256=b45bee3fd286f35d367ee25639100eb33b9244251d5a921dedd84c998e785a2d
```

### Attempt 2: PyTorch CDN host omitted

```text
code=PYTORCH_CDN_HOST_NOT_ALLOWED
historical_kaggle_title=auragateway-cu129-wheelhouse-cdn-mismatch-v1
observed_host=download-r2.pytorch.org
execution_log_sha256=69c7656374fc5313becb44684f1b11eac950db7c79eed5b62572eaefec3640a3
dependency_resolution_completed=true
wheel_downloads_performed=0
model_requests_performed=0
qualification_claimed=false
```

A fresh materializer notebook version may run only after the exact CDN host remediation is merged.
Do not rerun either failed saved version.
