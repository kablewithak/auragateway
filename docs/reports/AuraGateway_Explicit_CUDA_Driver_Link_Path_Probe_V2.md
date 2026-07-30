# AuraGateway explicit CUDA driver link-path probe V2

## Problem

Saved version `339111200` established:

```text
real libcuda mount present
runtime CUDA visible
exact C source compiled
default -lcuda search failed
```

The remaining question is whether the real driver contract passes when the
linker and executable are bound explicitly to `/usr/local/nvidia/lib64`.

## Probe contract

```text
P0:
  dual T4
  nvidia-smi
  base Torch CUDA
  real libcuda.so link
  compiler, ld, ldd, readelf

P1 V2:
  exact source
  one syntax compile
  one explicit link
  selected link artifact proof
  ELF NEEDED proof
  ELF RUNPATH proof
  ldd real-mount proof
  cuInit(0) == 0

P2:
  prohibited
```

## Failure taxonomy

```text
DIAGNOSTIC_INVALID
REAL_DRIVER_LINK_PATH_MISSING
CUDA_TOOLKIT_STUB_SELECTED
EXPLICIT_CUDA_DRIVER_LINK_FAILED
EXPLICIT_CUDA_DRIVER_ELF_CONTRACT_FAILED
EXPLICIT_CUDA_DRIVER_DYNAMIC_LOADER_FAILED
EXPLICIT_CUDA_DRIVER_INITIALIZATION_FAILED
```

Pass:

```text
EXPLICIT_CUDA_DRIVER_LINK_PATH_CONTRACT_PASSED
```

## Evidence assets

```text
platform_identity_report_v2.json
explicit_cuda_driver_link_report_v2.json
explicit_cuda_driver_link_summary_v2.json
bundle_manifest_v2.json
human_report_v2.md
ag-cu129-explicit-driver-link-evidence-v2.zip
```

## Safety

No Kaggle execution occurs in this repository tranche. The generated notebook
permits one bounded GPU session after merge, with Internet Off, no inputs, no
secrets, no runtime install, no Triton, no model, no worker and no request.

## Commercial proof angle

This is an AI System Evaluation Audit artifact. It separates driver mount,
linker search, selected link artifact, ELF contract, dynamic-loader resolution
and driver initialization.

A CTO pays because this prevents package churn, vendor blame and repeated GPU
spend before the actual native-toolchain boundary is identified.
