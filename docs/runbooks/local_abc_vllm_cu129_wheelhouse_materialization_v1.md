# AuraGateway vLLM CUDA 12.9 wheelhouse materialization and verification

## Current authorization

Offline verifier v3 Version 1 is preserved as valid diagnostic failure evidence. The exact governed
wheelhouse passed again, while the base Python 3.12.13 interpreter lacked the `ensurepip` module.
Package installation did not start and wheelhouse rematerialization is not justified.

```text
decision=APPROVED_FOR_OFFLINE_CU129_BASE_PIP_TARGET_INSTALL_VERIFICATION_V4
next_gate=run_cu129_offline_runtime_compatibility_verifier_v4
verifier_v3_evidence_zip_sha256=721fb2dc1fcbb57f2cda2e5772d5bac9fdf6f2f10798595fc4dd6f3cdf55d671
verifier_v3_evidence_manifest_sha256=399549e894f3d5afecffac1244d2bf32f32fb34c0f5ef815fba443b75f8613e8
materialization_receipt_sha256=52aa42b940dd606ab5685686ab893eb085efed2a7466989f654e870f4b360589
sha256_manifest_sha256=789fb23ab7d9c4f28dd909e808a53a65d692c0d7b43bc44da9e974817d771b8d
package_count=176
verifier_v3_status=FAILED
verifier_v3_input_validation=PASSED
verifier_v3_first_divergence=base_ensurepip_import
verifier_v3_failure_code=ENSUREPIP_MODULE_ABSENT
package_installation_started=false
wheelhouse_rematerialization_justified=false
installation_executor=BASE_PIP_PYTHON_TARGET
minimum_base_pip_version=22.3
active_verifier_notebook_sha256=b6a6e1ed7f33f98959fe346be173b1799a36aecb9e0245c9d2f3beaba1bd0568
```

The next action is one fresh verifier v4 run. It remains diagnostic only and may not load a model,
start workers, issue requests, create qualification authorization, or claim qualification.

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

## Consumed offline verifier v2

Verifier v2 Version 1 is immutable and must not be rerun.

```text
decision=APPROVED_FOR_OFFLINE_CU129_RUNTIME_COMPATIBILITY_VERIFICATION_V2
next_gate=run_cu129_offline_runtime_compatibility_verifier_v2
kaggle_title=auragateway-cu129-offline-verifier-v2
notebook_sha256=86db695b463a97d021c7d45a3cd31284d404d618c968ffd18837631f7221d5f2
evidence_zip_sha256=01019ce577f2bc7bfaaa8810d19161157f1dbc15b3c8817c2ba7836c4b0158d4
input_validation=PASSED
observed_failed_roles=["offline_isolated_install"]
first_divergence=venv.EnvBuilder(with_pip=True) -> ensurepip
failure_code=ENSUREPIP_BOOTSTRAP_FAILED
nested_ensurepip_output_captured=false
package_installation_started=false
```

The eight downstream required roles were not independently observed failures. They were absent because
the verifier scheduled them only after a successful isolated installation.

Do not rerun verifier v2.

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

## Consumed offline verifier v3

Verifier v3 Version 1 is immutable and must not be rerun.

```text
decision=APPROVED_FOR_OFFLINE_CU129_BOOTSTRAP_DIAGNOSTIC_VERIFICATION_V3
next_gate=run_cu129_offline_runtime_compatibility_verifier_v3
kaggle_title=auragateway-cu129-offline-verifier-v3
notebook_sha256=d9cd2218fb7fc995ecd205127d979154c9700d26e7432abfefc6a0a7af1af36f
evidence_zip_sha256=721fb2dc1fcbb57f2cda2e5772d5bac9fdf6f2f10798595fc4dd6f3cdf55d671
input_validation=PASSED
base_python_runtime=3.12.13
base_venv_import=PASSED
base_ensurepip_import=FAILED
first_divergence=base_ensurepip_import
failure_code=ENSUREPIP_MODULE_ABSENT
observed_failed_roles=["base_ensurepip_import"]
package_installation_started=false
wheelhouse_rematerialization_justified=false
```

The fourteen downstream roles were explicitly blocked by the first divergence. They were not
independently observed failures. GPU topology was also blocked by the v3 dependency graph, so verifier
v4 moves host GPU discovery into the independent probe stage.

Do not rerun verifier v3.

Repository notebook:

```text
notebooks/auragateway_vllm_cu129_offline_runtime_compatibility_v3.ipynb
```

Requested Kaggle title:

```text
auragateway-cu129-offline-verifier-v3
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

Verifier v3 preserves the exact wheelhouse validation from v2, then separates bootstrap into explicit
captured roles:

```text
base_python_runtime
base_venv_import
base_ensurepip_import
base_ensurepip_cli
venv_create_without_pip
venv_python_runtime
venv_ensurepip_bootstrap
venv_pip_version
offline_hash_locked_install
```

It creates the environment with `--without-pip`, invokes the new interpreter's `ensurepip` as a
separately captured subprocess, and starts the exact `--no-index --require-hashes` installation only
after bootstrap passes.

Downstream roles use this taxonomy:

```text
FAILED
BLOCKED_BY_UPSTREAM_FAILURE
NOT_EXECUTED
```

Required output artifact:

```text
/kaggle/working/auragateway_vllm_cu129_offline_compatibility_evidence_v3.zip
```

Run exactly once with `Save Version -> Save & Run All`. Preserve Version 1 whether the result passes or
fails. Upload only the evidence ZIP and complete execution log, then turn both GPUs off.

## Active offline verifier v4

Repository notebook:

```text
notebooks/auragateway_vllm_cu129_offline_runtime_compatibility_v4.ipynb
```

Requested Kaggle title:

```text
auragateway-cu129-offline-verifier-v4
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

Verifier v4 preserves the exact wheelhouse validation and runs these host-independent probes even when
target installation cannot proceed:

```text
base_python_runtime
base_venv_import
base_pip_import
base_distribution_snapshot_before
gpu_topology
```

It then creates a clean target with `venv --without-pip`, validates target isolation, and invokes base
pip only as an installation executor:

```text
<base-python> -m pip
  --isolated
  --disable-pip-version-check
  --python <target-venv>
  install
  --no-index
  --no-cache-dir
  --find-links <wheelhouse>
  --require-hashes
  -r <requirements-lock>
```

The global `--python` option must precede the `install` subcommand. Verifier v4 requires base pip 22.3
or newer, validates the exact 176-distribution target inventory, runs target dependency checking through
base pip, and compares base distribution metadata snapshots before and after the attempt.

Downstream roles retain this taxonomy:

```text
FAILED
BLOCKED_BY_UPSTREAM_FAILURE
NOT_EXECUTED
```

Required output artifact:

```text
/kaggle/working/auragateway_vllm_cu129_offline_compatibility_evidence_v4.zip
```

Run exactly once with `Save Version -> Save & Run All`. Preserve Version 1 whether the result passes or
fails. Upload only the evidence ZIP and complete execution log, then turn both GPUs off.

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
