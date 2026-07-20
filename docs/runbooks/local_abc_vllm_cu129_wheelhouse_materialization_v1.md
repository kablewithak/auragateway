# AuraGateway vLLM CUDA 12.9 wheelhouse materialization and verification

## Current authorization

The exact-lock CPU materializer completed successfully and its small control-plane evidence has been
integrated. The next authorized action is one fresh offline runtime compatibility verifier v2.

```text
decision=APPROVED_FOR_OFFLINE_CU129_RUNTIME_COMPATIBILITY_VERIFICATION_V2
next_gate=run_cu129_offline_runtime_compatibility_verifier_v2
materialization_receipt_sha256=52aa42b940dd606ab5685686ab893eb085efed2a7466989f654e870f4b360589
sha256_manifest_sha256=789fb23ab7d9c4f28dd909e808a53a65d692c0d7b43bc44da9e974817d771b8d
resolution_lock_sha256=1575538b0a412c9b030fc95ccada0f0527553b76f06ef6b2b72904e61c84870c
package_count=176
manifest_entry_count=182
wheel_entry_count=176
non_wheel_entry_count=6
total_wheel_bytes=5727339111
active_verifier_notebook_sha256=86db695b463a97d021c7d45a3cd31284d404d618c968ffd18837631f7221d5f2
```

The verifier remains diagnostic only. It may install the wheelhouse into a fresh isolated virtual
environment and test imports, but it may not load a model, start workers, issue requests, create an
authorization, or claim qualification.

## Materialization result

```text
notebook=notebooks/auragateway_vllm_cu129_wheelhouse_materialization_v1.ipynb
kaggle_title=auragateway-cu129-wheelhouse-materializer-v1
output_directory=auragateway_vllm_cu129_wheelhouse_v1
materializer_notebook_sha256=d836a61bc7ed7a0d6c26eca68a28ed22e685e5a6705bf16ce4f6dbb8168f7ba2
execution_log_sha256=65387a9952bce57d1802ebd8e39dc58dd897d50680debb70f3422c52c4ef5538
materialization_status=PASSED
package_installation_performed=false
model_requests_performed=0
qualification_claimed=false
```

The wheelhouse contains 176 exact locked distributions and 5,727,339,111 wheel bytes. The
`sha256_manifest.json` contains exactly 182 unique entries:

```text
176 wheel entries
6 governed non-wheel entries
```

The six non-wheel manifest entries are:

```text
requirements.in
resolution_lock.json
materialization.lock.txt
requirements.lock.txt
install_runtime.py
runtime_manifest.json
```

The receipt and SHA-256 manifest are top-level control artifacts and are validated by exact external
identities rather than recursively including themselves.

Do not rerun the successful materializer.

## Preserved reconnaissance evidence

```text
reconnaissance_notebook=auragateway-cu129-resolution-reconnaissance-v1
reconnaissance_result=RECONNAISSANCE_ACCEPTED_AND_LOCKED
resolution_lock_sha256=1575538b0a412c9b030fc95ccada0f0527553b76f06ef6b2b72904e61c84870c
historical_failure_code=NVIDIA_PACKAGE_HOST_NOT_ALLOWED
historical_failure_log_sha256=f6e6f844ebfb7ede0aab428e4766af4123622fb2f3092933e4070e26d6831fa4
historical_observed_host=pypi.nvidia.com
```

The approved exact-host closure includes `download-r2.pytorch.org` and `pypi.nvidia.com` only for
the exact locked artifacts. Wildcard domains remain prohibited.

Do not summarize this evidence as zero downloads. Resolution-time artifact transfer and persistent
wheel downloads are recorded as separate events.

## Superseded offline verifier v1

The unexecuted verifier v1 is preserved as static defect evidence:

```text
repository_notebook=notebooks/auragateway_vllm_cu129_offline_runtime_compatibility_v1.ipynb
kaggle_title=auragateway-cu129-offline-verifier-v1
evidence_directory=auragateway_vllm_cu129_offline_compatibility_evidence_v1
notebook_sha256=692f83fd8a6fa7398ee9fabb0ecbf62640c82d6582a96a552f47e4f8b3b1b189
execution_authority=SUPERSEDED_BEFORE_EXECUTION
diagnostic_admissibility=STATIC_DEFECT_EVIDENCE_ONLY
defect_code=OFFLINE_VERIFIER_TOPOLOGY_CONTRACT_OMITS_RESOLUTION_LOCK
```

Its exact top-level topology omitted `resolution_lock.json`, although the successful materializer
output necessarily contains that file. Running it would fail before installation with
`wheelhouse top-level topology drifted`.

Do not import or run verifier v1.

## Active offline verifier v2

Repository notebook:

```text
notebooks/auragateway_vllm_cu129_offline_runtime_compatibility_v2.ipynb
```

Requested Kaggle title:

```text
auragateway-cu129-offline-verifier-v2
```

Character count:

```text
37
```

Settings:

```text
Accelerator: T4 x2
Internet: Off
Secrets: None
Inputs: exactly the successful Version 1 materializer output
```

Attach exactly one input containing:

```text
auragateway_vllm_cu129_wheelhouse_v1/
├── wheels/
├── requirements.in
├── resolution_lock.json
├── materialization.lock.txt
├── requirements.lock.txt
├── install_runtime.py
├── runtime_manifest.json
├── sha256_manifest.json
└── materialization_receipt.json
```

Do not attach a model snapshot, harness, qualification authorization, control output, rejected
wheelhouse, or any customer data.

The verifier first performs a full streaming SHA-256 and size check of all 182 manifest entries,
validates the exact 176-package resolution closure, validates both locks and all control identities,
and confirms sufficient writable disk. It then executes:

```text
offline isolated installation with --no-index
pip check
two-T4 topology check
Python 3.12 check
torch 2.10.0+cu129 check
torchaudio 2.10.0+cu129 check
torchvision 0.25.0+cu129 check
CUDA 12.9 check
Transformers 5.5.3 check
vLLM distribution 0.19.1 check
vLLM module import
vLLM native-extension import
```

Run exactly once:

```text
Save Version
→ Save & Run All
```

Suggested version description:

```text
Verify exact-locked CUDA 12.9 wheelhouse offline
```

Required output directory:

```text
/kaggle/working/auragateway_vllm_cu129_offline_compatibility_evidence_v2/
```

Required output artifact:

```text
/kaggle/working/auragateway_vllm_cu129_offline_compatibility_evidence_v2.zip
```

Required terminal fields:

```text
offline_compatibility_status=PASSED
failed_required_roles=[]
model_requests_performed=0
qualification_claimed=false
upload_only_this_file=true
```

If any input or runtime gate fails, preserve Version 1 and upload the evidence ZIP and execution log.
Do not edit or rerun the notebook to force a pass.

## Stop policy

After the verifier finishes:

1. Preserve immutable Version 1.
2. Download only the verifier evidence ZIP and complete execution log.
3. Close the Kaggle session and turn GPUs off.
4. Stop before model loading, worker startup, or measured A/B/C execution.

No model requests or qualification are authorized by this runbook.

## Preserved failed materializer attempts

### Attempt 1: explicit cu128 asset absent

```text
code=VLLM_CU128_RELEASE_ASSET_ABSENT
execution_log_sha256=b45bee3fd286f35d367ee25639100eb33b9244251d5a921dedd84c998e785a2d
wheel_downloads_performed=0
model_requests_performed=0
qualification_claimed=false
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

### Attempt 3: NVIDIA package host omitted

```text
code=NVIDIA_PACKAGE_HOST_NOT_ALLOWED
historical_kaggle_title=auragateway-cu129-wheelhouse-nvidia-host-mismatch-v1
observed_host=pypi.nvidia.com
execution_log_sha256=f6e6f844ebfb7ede0aab428e4766af4123622fb2f3092933e4070e26d6831fa4
dependency_resolution_completed=true
wheel_downloads_performed=0
model_requests_performed=0
qualification_claimed=false
```
