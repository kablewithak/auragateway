# ADR: Accept the exact-locked CUDA 12.9 wheelhouse and supersede verifier v1

Status: Accepted

Date: 2026-07-20

## Context

The governed CPU-only materializer completed successfully against the reviewed 176-package CUDA
12.9 closure.

```text
materialization_status=PASSED
package_count=176
manifest_entry_count=182
wheel_entry_count=176
non_wheel_entry_count=6
total_wheel_bytes=5727339111
materialization_receipt_sha256=52aa42b940dd606ab5685686ab893eb085efed2a7466989f654e870f4b360589
sha256_manifest_sha256=789fb23ab7d9c4f28dd909e808a53a65d692c0d7b43bc44da9e974817d771b8d
resolution_lock_sha256=1575538b0a412c9b030fc95ccada0f0527553b76f06ef6b2b72904e61c84870c
package_installation_performed=false
model_requests_performed=0
qualification_claimed=false
```

The materializer output contains nine top-level members, including `resolution_lock.json`.

The previously merged offline verifier v1 required an exact top-level set that omitted
`resolution_lock.json`. Its static contract would therefore reject the successful governed
wheelhouse before installation.

```text
defect_code=OFFLINE_VERIFIER_TOPOLOGY_CONTRACT_OMITS_RESOLUTION_LOCK
execution_authority=SUPERSEDED_BEFORE_EXECUTION
diagnostic_admissibility=STATIC_DEFECT_EVIDENCE_ONLY
```

## Decision

1. Accept the materialization result as evidence that the exact 176-package wheelhouse was retained.
2. Preserve the materializer Version 1 and do not rerun it.
3. Preserve verifier v1 unchanged as static defect evidence.
4. Do not execute verifier v1.
5. Introduce verifier v2 with exact input topology and exact materialization evidence bindings.
6. Authorize one fresh verifier v2 run on Kaggle with T4 x2, Internet Off, no secrets, and exactly
   the successful materializer output as input.
7. Stop after offline installation, dependency checks, GPU/runtime checks, and native import checks.
8. Do not load a model, start workers, issue requests, create qualification authorization, or run
   measured A/B/C trajectories.

Active verifier:

```text
repository_notebook=notebooks/auragateway_vllm_cu129_offline_runtime_compatibility_v2.ipynb
kaggle_title=auragateway-cu129-offline-verifier-v2
notebook_sha256=86db695b463a97d021c7d45a3cd31284d404d618c968ffd18837631f7221d5f2
output_directory=auragateway_vllm_cu129_offline_compatibility_evidence_v2
```

The requested Kaggle title has 37 characters.

Verifier v2 binds:

```text
materialization_receipt_sha256=52aa42b940dd606ab5685686ab893eb085efed2a7466989f654e870f4b360589
sha256_manifest_sha256=789fb23ab7d9c4f28dd909e808a53a65d692c0d7b43bc44da9e974817d771b8d
runtime_manifest_sha256=b424d2b952d726b2f7451ebd8f48d604985f650dbe2f6d146969625618b7fc51
materialization_lock_sha256=d061bd9a7ff0a686bb462a2bd016a1f3e1aea833fbdbff353dddf96fdd623e1d
requirements_lock_sha256=47cb357a53ca74ca597b286768e1d0e9cb831f7431c08fad378fc42ea59b3a27
install_runtime_sha256=68bba3ca131e9a6f36392330562985d2a644be57cf5437fd282b883741c86821
requirements_in_sha256=a120c72a5643bb65afbfe0bd3dd072f1ea89a19f57a534dd814c9bafdd41880f
```

## Consequences

The next gate can detect:

- missing or unexpected wheelhouse members;
- path traversal or symlink substitution;
- wheel size or SHA-256 drift;
- resolution-lock-to-wheel mismatch;
- materialization-lock or requirements-lock mismatch;
- insufficient writable disk;
- offline installation failure;
- dependency inconsistency;
- GPU topology drift;
- Torch, CUDA, Torchaudio, Torchvision, Transformers, or vLLM version drift;
- vLLM module or native-extension import failure.

The repository does not retain the 5.7 GB wheelhouse. It retains only small control-plane evidence,
hashes, manifests, locks, receipt, and execution log.

## Non-claims

This decision does not establish:

- successful offline installation;
- successful `pip check`;
- successful Torch CUDA runtime initialization;
- successful vLLM module or native-extension import;
- model or tokenizer loading;
- worker health;
- cache telemetry availability;
- environment qualification;
- authorization for measured A/B/C execution;
- production readiness.
