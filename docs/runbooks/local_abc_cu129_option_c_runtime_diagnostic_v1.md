# Runbook: Option C CUDA 12.9 runtime diagnostic

## Purpose

Define the execution boundary for Option C without authorizing execution.

## Current allowed work

This tranche may:

- add and validate the Option C decision contract;
- document P0-P2 and P3-P6;
- prepare the next implementation boundary.

This tranche may not:

- modify runtime source;
- modify canonical worker commands;
- issue authorization;
- run Kaggle;
- load the model;
- start a worker;
- perform model requests;
- execute benchmark trajectories.

## P0-P2 platform diagnostic

### P0 — image and runtime identity

Capture, without model load:

```text
Kaggle image or build identity
GPU names and compute capabilities
driver version
Python version
PyTorch version and CUDA build
LD_LIBRARY_PATH
LIBRARY_PATH
CUDA_HOME
libcuda.so and libcuda.so.1 locations
compiler and linker identity
ptxas path and version
loaded package and module origins
```

Failure to capture required identity fields returns:

```text
DIAGNOSTIC_INVALID
```

### P1 — CUDA driver linker visibility

Perform one bounded compile-and-link test using `-lcuda`.

The probe must distinguish:

```text
runtime-visible real driver library
linker-visible library name
CUDA toolkit stub
missing or ambiguous resolution
```

Prohibited:

```text
creating a libcuda.so symlink
copying a driver library
changing a system directory
placing a CUDA stub in a runtime loader path
continuing after an ambiguous result
```

Failure returns:

```text
CURRENT_KAGGLE_IMAGE_LINKER_CONTRACT_FAILED
```

### P2 — minimal Triton kernel

Compile and execute one minimal Triton kernel using the pinned runtime.

The probe must record:

```text
Triton distribution and module version
module origin
GPU architecture
compiler path
ptxas path
compile status
execution status
bounded error classification
```

Failure returns:

```text
CURRENT_STACK_TRITON_INCOMPATIBLE
```

## Execution budgets

```text
maximum Kaggle sessions: 1
model load: 0
worker starts: 0
model requests: 0
benchmark trajectory requests: 0
network access: prohibited
credentials: prohibited
customer data: prohibited
external spend: 0
hidden retries: prohibited
```

## Terminal semantics

Stop at the first failed probe.

Later commands and success markers from the same old block are invalid after a
failure.

No unchanged rerun is permitted. Preserve the evidence and classify the first
divergence.

## P3-P6 boundary

P3-P6 are deferred until explicit `TRITON_ATTN` is implemented and merged.

They require a separate future authorization and frozen request budget.

## Required P0-P2 outputs

The future implementation must produce:

```text
platform_identity_report.json
cuda_driver_linker_report.json
minimal_triton_kernel_report.json
option_c_platform_diagnostic_summary.json
bundle_manifest.json
human_report.md
```

Missing fields remain missing or unresolved. They must never be converted to a
successful zero value.

## Non-claims

P0-P2 cannot prove model serving, worker readiness, cache reuse, reset,
dual-worker isolation, measured A/B/C effect, or production readiness.
