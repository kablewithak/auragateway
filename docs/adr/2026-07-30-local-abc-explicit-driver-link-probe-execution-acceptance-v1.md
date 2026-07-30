# ADR: Accept the explicit CUDA driver-link probe V2 execution

- Status: Accepted for evidence integration
- Date: 2026-07-30
- Integration base: `147c2a886af71a97d38474be5ffb718442e551e8`
- Kaggle saved version: `339127349`
- Saved-version URL:
  `https://www.kaggle.com/code/kabomolefe/ag-cu129-explicit-driver-link-probe-v2/log?scriptVersionId=339127349`

## Context

The earlier P0–P2 diagnostic failed at default native `-lcuda` resolution even
though the real NVIDIA driver mount and a working CUDA runtime were present.

The standalone V2 probe tested the smallest causal intervention: add the real
driver directory and command-local RUNPATH to one native link command while
rejecting the CUDA toolkit stub and avoiding global environment mutation.

## Evidence

```text
execution log SHA-256:
cedffa52fda554e68f03cf6c0c623e090a634ecb3e0bcfa808ebc3e97e9d293a

evidence ZIP SHA-256:
8be080c46a077d88dcd0d51325fe2a751936a599d3b350ba7def3bdf5eb7b33c
```

The execution passed:

```text
EXPLICIT_CUDA_DRIVER_LINK_PATH_CONTRACT_PASSED
```

The link trace selected:

```text
/usr/local/nvidia/lib64/libcuda.so.580.159.04
```

ELF and runtime resolution proved:

```text
NEEDED  = libcuda.so.1
RUNPATH = /usr/local/nvidia/lib64
ldd     = /usr/local/nvidia/lib64/libcuda.so.1
cuInit(0) = 0
```

## Decision

Accept the execution as proof that the earlier P1 failure was a default linker
search-path defect, not driver absence.

The maintainable realization is:

```text
command-local -L/usr/local/nvidia/lib64
command-local RUNPATH=/usr/local/nvidia/lib64
link-trace inspection
ELF inspection
runtime-loader inspection
cuInit(0)
```

Global `LIBRARY_PATH` or `LD_LIBRARY_PATH` mutation is not required. CUDA
toolkit stub linking is not required and remains prohibited.

## Sequencing decision

Integrate the accepted evidence in its own PR before implementing P0–P2
diagnostic V2.

This preserves:

- immutable external evidence;
- a queryable acceptance record;
- independent rollback;
- clean review boundaries;
- implementation freedom without rewriting the runtime conclusion.

## Next gate

`DESIGN_AND_IMPLEMENT_P0_P2_PLATFORM_DIAGNOSTIC_V2`

## Non-claims

This evidence does not prove CUDA 12.9 wheelhouse installation, Triton
compatibility, P2, vLLM startup, model inference, measured A/B/C, deployment or
production readiness.
