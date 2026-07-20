# CUDA 12.9 controlled Python startup verifier v6

## Current authorization

```text
decision=APPROVED_FOR_OFFLINE_CU129_CONTROLLED_PYTHON_STARTUP_VERIFICATION_V6
next_gate=run_cu129_offline_runtime_compatibility_verifier_v6
repository_base_commit=eb81a61a99f6839794a0ea4c4f90b2cb8dc7e4f3
verifier_v6_notebook_sha256=48d4ee3a9dfce1eb4634a37e9e75fc5042d11d30cb0860c8455e8815c3b4e4f0
decision_record_sha256=4d8e439e652916892777272219784c7197c849dbf26717f2e7403d1acfd9813a
python_startup_policy=NO_SITE_WITH_CONTROLLED_SITE_BOOTSTRAP
canonical_loader_policy=TARGET_NVIDIA_LIBRARIES_PREPENDED
wheelhouse_rematerialization_justified=false
package_version_substitution_justified=false
model_requests_permitted=0
qualification_claimed=false
```

Verifier v5 Version 1 and the startup inspection Version 1 are immutable and must not be rerun.

## Kaggle configuration

```text
Title: auragateway-cu129-offline-verifier-v6
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

Do not attach verifier evidence, the startup inspection, models, harness artifacts, qualification records, secrets, customer data, or extra datasets.

## Runtime sequence

1. Validate all 182 wheelhouse manifest entries and the exact 176-package closure.
2. Capture base Python, base pip, distribution snapshot, and T4 x2 topology.
3. Create the target virtual environment with `--without-pip`.
4. Run the pre-install target identity through the controlled Python startup wrapper.
5. Use base pip `--python <target>` for the exact offline hash-locked installation.
6. Validate target inventory and dependencies.
7. Build target-first CUDA library ordering.
8. Validate nvJitLink resolution and the CUDA 12.9 symbol.
9. Run direct cuSPARSE loading, target-process isolation, Torch, Transformers, vLLM, and `vllm._C` through the controlled wrapper.
10. Compare base distribution metadata snapshots.

## Execution

Run exactly once:

```text
Save Version
→ Save & Run All
```

Version description:

```text
Verify CUDA 12.9 with controlled Python startup
```

Required output:

```text
/kaggle/working/auragateway_vllm_cu129_offline_compatibility_evidence_v6.zip
```

Preserve Version 1 whether it passes or fails. Download only the evidence ZIP and complete execution log. Turn both GPUs off immediately afterward.

## Stop policy

No model or tokenizer loading, worker startup, model request, benchmark trajectory, qualification authorization, customer data, credentials, or external spend is permitted.
