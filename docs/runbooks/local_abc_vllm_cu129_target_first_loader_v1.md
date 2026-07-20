# AuraGateway CUDA 12.9 target-first loader verification

## Purpose

This runbook governs the transition from immutable verifier v4 and dynamic-linker inspection evidence
to one verifier v5 execution. It does not replace or mutate the historical wheelhouse-materialization
runbook.

## Consumed verifier v4

```text
decision=APPROVED_FOR_OFFLINE_CU129_BASE_PIP_TARGET_INSTALL_VERIFICATION_V4
next_gate=run_cu129_offline_runtime_compatibility_verifier_v4
kaggle_title=auragateway-cu129-offline-verifier-v4
evidence_zip_sha256=9a4bd10a66c440ffb2628f98ce143e38a1b5cdb06a745497b7b386910816e0fe
package_count=176
offline_hash_locked_install_via_base_pip=PASSED
target_distribution_inventory=PASSED
target_dependency_check_via_base_pip=PASSED
first_divergence=torch_family_runtime
failure_code=NVJITLINK_12_9_SYMBOL_UNRESOLVED
model_requests_performed=0
qualification_claimed=false
```

Do not rerun verifier v4.

## Consumed dynamic-linker inspection

```text
inspection_evidence_zip_sha256=b241f49a4636c6e427299582c130f4742cf925ad5f541a65f852fa424457d2d0
inspection_status=COMPLETED
root_cause_assignment=LOADER_PRECEDENCE_CONFIRMED
required_symbol=__nvJitLinkGetErrorLogSize_12_9
governed_nvjitlink_sha256=02d3acb5fe598dd20f0fca3cc03734ad164037a22747a01900561a42d0b8448f
governed_cusparse_sha256=6d85ab1acdabfe3b5a54aa76bc948c719bcd03e07eede3eb8122b083c1a6ecf7
inherited_environment_load_status=FAILED
target_first_environment_load_status=PASSED
package_installation_performed=false
model_requests_performed=0
qualification_claimed=false
```

Do not rerun the dynamic-linker inspection.

## Active verifier v5

```text
decision=APPROVED_FOR_OFFLINE_CU129_TARGET_FIRST_LOADER_VERIFICATION_V5
next_gate=run_cu129_offline_runtime_compatibility_verifier_v5
repository_notebook=notebooks/auragateway_vllm_cu129_offline_runtime_compatibility_v5.ipynb
kaggle_title=auragateway-cu129-offline-verifier-v5
notebook_sha256=ad4d7a533de09965f5562db58c85cb785f2a7f8550906631142e26a34b6e59ab
output_directory=auragateway_vllm_cu129_offline_compatibility_evidence_v5
canonical_loader_policy=TARGET_NVIDIA_LIBRARIES_PREPENDED
wheelhouse_rematerialization_justified=false
package_version_substitution_justified=false
model_requests_performed=0
qualification_claimed=false
```

Settings:

```text
Accelerator: T4 x2
Internet: Off
Secrets: None
Inputs: exactly the successful Version 1 materializer output
```

Verifier v5 preserves the exact 176-package offline closure. The phrase `zero downloads` applies only
to this offline verifier execution; it does not rewrite the recorded materialization history.

Canonical process policy:

```text
PYTHONPATH=<removed>
PYTHONHOME=<removed>
PYTHONNOUSERSITE=1
LD_LIBRARY_PATH=<target NVIDIA libraries first>:<inherited libraries second>
VIRTUAL_ENV=<target>
PATH=<target>/bin:<inherited PATH>
```

Before Torch import, verifier v5 must prove target library identity, required nvJitLink symbol
availability, target-first `ldd` resolution, direct cuSPARSE loading, and target Python-path isolation.

Run exactly once with `Save Version -> Save & Run All`. Preserve Version 1 whether the result passes or
fails. Download only the evidence ZIP and complete execution log, close the session, and turn both GPUs
off.

No model loading, tokenizer loading, worker startup, model request, benchmark trajectory, qualification
authorization, or production-readiness claim is permitted.
