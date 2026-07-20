# CUDA 12.9 target-directory installation verifier v7

## Current authorization

```text
decision=APPROVED_FOR_OFFLINE_CU129_TARGET_DIRECTORY_INSTALL_VERIFICATION_V7
next_gate=run_cu129_offline_runtime_compatibility_verifier_v7
repository_base_commit=cafddfb46c1e2b8eecd830dc21aad0fc0b982200
verifier_v7_notebook_sha256=66fe0df31e49c035d858865749eca1755d5d09ce863b378a9f01fb55ac8bf7fd
decision_record_sha256=69e057564f0f215095f1fde4244fc526905f79646c1dfe79d3e670f63b74cd22
reasoning_certificate_sha256=e803966fdaa11714c68a2d6d4ebb4f42da80b686251821d88da658758e798a0d
installation_executor=BASE_PIP_TARGET_DIRECTORY
dependency_validation=CONTROLLED_TARGET_METADATA_AND_PACKAGING
python_startup_policy=NO_SITE_WITH_CONTROLLED_SITE_BOOTSTRAP
canonical_loader_policy=TARGET_NVIDIA_LIBRARIES_PREPENDED
wheelhouse_rematerialization_justified=false
package_version_substitution_justified=false
model_requests_permitted=0
qualification_claimed=false
```

Verifier v6, installation inspection v1, and installation inspection v2 are immutable Version 1
evidence and must not be rerun.

## Kaggle configuration

```text
Title: auragateway-cu129-offline-verifier-v7
Character count: 37
Accelerator: T4 x2
Internet: Off
Secrets: None
Inputs: exactly the successful Version 1 materializer output
```

Attach exactly one input exposing:

```text
auragateway_vllm_cu129_wheelhouse_v1
```

Do not attach verifier evidence, inspection evidence, models, harness artifacts, qualification
records, secrets, customer data, or extra datasets.

## Runtime sequence

1. Validate all 182 wheelhouse manifest entries and the exact 176-package closure.
2. Capture base Python, base pip, base distribution snapshot, and T4 x2 topology.
3. Create the target virtual environment with `--without-pip`.
4. Validate pre-install target identity through the controlled Python startup wrapper.
5. Install the exact closure with base pip into the explicit target site-packages directory:

```text
python -m pip --isolated --disable-pip-version-check install
  --no-index
  --no-cache-dir
  --no-deps
  --ignore-installed
  --find-links <wheelhouse>/wheels
  --require-hashes
  --target <venv>/lib/python3.12/site-packages
  -r <wheelhouse>/requirements.lock.txt
```

6. Validate the exact 176-distribution target inventory.
7. Evaluate active dependency metadata through the controlled target interpreter.
8. Build the target-first CUDA library ordering.
9. Validate inherited and canonical nvJitLink resolution and the CUDA 12.9 symbol.
10. Run direct cuSPARSE loading, process-isolation, Python, Torch, Transformers, vLLM, and
    `vllm._C` probes.
11. Compare base distribution metadata before and after.
12. Emit one bounded evidence ZIP whether the verifier passes or fails.

## Success gate

```text
offline_compatibility_status=PASSED
first_divergence=None
failed_required_roles=[]
blocked_required_roles=[]
not_executed_required_roles=[]
canonical_nvjitlink_resolved_to_target=true
target_process_environment_isolated=true
base_distribution_metadata_unchanged=true
model_requests_performed=0
qualification_claimed=false
```

## Failure handling

Preserve Version 1 and upload only the evidence ZIP and complete execution log. Do not edit or
rerun verifier v7. Do not rematerialize the wheelhouse or substitute package versions without a
new evidence-backed repository decision.

## Non-claims

A passing verifier v7 establishes only offline package/runtime compatibility for this exact Kaggle
image, wheelhouse, startup policy, and loader policy. It does not load a model, start a worker,
issue a request, qualify the environment, authorize measured A/B/C, or establish production
readiness.
