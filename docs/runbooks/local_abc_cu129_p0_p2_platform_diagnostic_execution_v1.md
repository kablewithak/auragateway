# Runbook: CUDA 12.9 P0-P2 platform diagnostic execution

## Purpose

Execute the model-free Option C platform diagnostic exactly once on Kaggle
before changing the canonical vLLM worker runtime.

The diagnostic answers:

```text
P0 — what exact Kaggle image and CUDA environment is active?
P1 — can the active image link and execute a minimal -lcuda program?
P2 — can the pinned CUDA 12.9 runtime compile and execute one Triton kernel?
```

## Governing identities

```text
source main merge:
f4f08eda4b4d4747514b4646fe53664d8a78ca6d

notebook:
notebooks/auragateway_cu129_p0_p2_platform_diagnostic_v1.ipynb

Kaggle notebook name:
ag-cu129-p0-p2-platform-diagnostic-v1

failed-run rename:
ag-cu129-p0-p2-platform-diag-failed-v1

evidence ZIP:
ag-cu129-p0-p2-platform-evidence-v1.zip
```

Both notebook names are below Kaggle's 50-character limit.

## Required Kaggle configuration

Configure one notebook version with:

```text
accelerator: GPU T4 x2
Internet: Off
secrets: none
credentials: none
customer data: none
external spend: 0
```

Attach the existing governed CUDA 12.9 wheelhouse output containing exactly one
directory named:

```text
auragateway_vllm_cu129_wheelhouse_v1
```

Do not attach the model snapshot. P0-P2 prohibit model loading.

## Execution procedure

1. Upload or create the exact reviewed notebook.
2. Set the notebook name to
   `ag-cu129-p0-p2-platform-diagnostic-v1`.
3. Select dual Tesla T4.
4. Disable Internet.
5. Attach only the governed CUDA 12.9 wheelhouse input.
6. Save and run one notebook version.
7. Do not edit or rerun the same lineage after a diagnostic failure.
8. Preserve the generated evidence ZIP and notebook log.
9. If the run fails operationally, rename that failed notebook lineage to
   `ag-cu129-p0-p2-platform-diag-failed-v1` before creating any corrected
   successor.

## Stop-on-first-failure behavior

The notebook always writes the required output set, but it does not execute a
later probe after an earlier probe fails.

```text
P0 failure:
  P1 = NOT_RUN_DUE_TO_PRIOR_FAILURE
  P2 = NOT_RUN_DUE_TO_PRIOR_FAILURE
  terminal decision = DIAGNOSTIC_INVALID

P1 failure:
  P2 = NOT_RUN_DUE_TO_PRIOR_FAILURE
  terminal decision = CURRENT_KAGGLE_IMAGE_LINKER_CONTRACT_FAILED

P2 failure:
  terminal decision = CURRENT_STACK_TRITON_INCOMPATIBLE

P0-P2 pass:
  terminal decision = P0_P2_PLATFORM_DIAGNOSTIC_PASSED
```

No unchanged rerun is permitted.

## Required outputs

The evidence ZIP must contain exactly:

```text
platform_identity_report.json
cuda_driver_linker_report.json
minimal_triton_kernel_report.json
option_c_platform_diagnostic_summary.json
bundle_manifest.json
human_report.md
```

## P0 evidence

P0 captures only allowlisted environment fields and bounded command output:

```text
BUILD_DATE
GIT_COMMIT
KAGGLE_KERNEL_RUN_TYPE
KAGGLE_CONTAINER_NAME
LD_LIBRARY_PATH
LIBRARY_PATH
CUDA_HOME
CUDA_PATH
Python and OS identity
two-GPU topology
Tesla T4 names
compute capability 7.5
driver version
base Torch and Triton origins
cc, gcc, ld, nvcc, ptxas, and ldconfig identity
libcuda candidates
ctypes CUDA-library discovery
```

Raw environment dumps are prohibited.

## P1 evidence

P1 performs one compile, link, and execution attempt:

```text
cc cuda_driver_link_probe.c -Wl,-t -lcuda -o cuda_driver_link_probe
ldd cuda_driver_link_probe
cuda_driver_link_probe
```

The probe records:

```text
selected link-time libcuda path
link-time library classification
runtime libcuda.so.1 path
runtime-library classification
cuInit return status
```

It does not:

```text
create a symlink
copy a driver library
change a system directory
add an ad hoc -L path
place CUDA stubs in a runtime loader path
retry with alternative commands
```

## P2 evidence

P2 runs only after P0 and P1 pass.

It:

1. discovers exactly one governed wheelhouse;
2. validates all pinned control hashes;
3. validates every checksum-manifest entry;
4. installs the complete runtime with `--no-index` and `--require-hashes`;
5. prepends only the installed NVIDIA package library directories;
6. exposes GPU 0 to one bounded process;
7. compiles and executes one vector-add Triton kernel;
8. checks the exact result;
9. records Torch, CUDA, Triton, module-origin, GPU, and compiler evidence.

It does not import vLLM, load a model, start a server, or send a request.

## Review procedure after execution

Inspect:

```text
option_c_platform_diagnostic_summary.json
bundle_manifest.json
human_report.md
```

Then verify:

```text
model_loads = 0
worker_starts = 0
model_requests = 0
benchmark_trajectory_requests = 0
network_requests = 0
hidden_retries_performed = 0
full_triton_qualification_attempt_consumed = false
```

## Decision transitions

### Passed

```text
terminal_decision = P0_P2_PLATFORM_DIAGNOSTIC_PASSED
next_gate = implement_explicit_triton_attention_backend
```

### Failed

Preserve the complete evidence and classify the first divergence. Do not begin
runtime implementation until a new decision explicitly authorizes it.

## Non-claims

P0-P2 do not prove:

- vLLM startup;
- explicit `TRITON_ATTN` realization;
- model inference;
- prefix-cache telemetry;
- reset behavior;
- dual-worker readiness;
- environment qualification;
- measured A/B/C effects;
- deployment;
- customer-data validation;
- production readiness.
