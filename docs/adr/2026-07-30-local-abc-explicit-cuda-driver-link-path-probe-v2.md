# ADR: Standalone explicit CUDA driver link-path probe V2

- Status: Accepted for implementation
- Date: 2026-07-30
- Repository base: `f7ed2a6aec0fe47b3cde3941c476af10fb70a291`
- Prior saved version: `339111200`
- Execution in this tranche: prohibited

## Context

The corrected P0-P2 diagnostic proved that the current Kaggle runtime mounted
a real CUDA driver library under `/usr/local/nvidia/lib64`, while the default
native linker search failed to resolve `-lcuda`.

The next experiment must isolate explicit link-path realization without
repeating the prior probe unchanged and without mixing in runtime installation,
Triton, vLLM, models, workers or benchmark traffic.

## Decision

Create a separate producer-owned P0 plus P1 V2 notebook:

```text
ag-cu129-explicit-driver-link-probe-v2
```

It will:

1. verify dual T4 topology and the real driver mount;
2. reject the CUDA toolkit stub directory;
3. materialize the exact governed C source;
4. compile the source exactly once;
5. link exactly once with:
   - `-L/usr/local/nvidia/lib64`
   - `-Wl,-rpath,/usr/local/nvidia/lib64`
   - `-Wl,-t`
   - `-lcuda`
6. prove the selected link library is under the real driver mount;
7. inspect ELF `NEEDED` and `RUNPATH`;
8. require `ldd` to resolve `libcuda.so.1` under the real mount;
9. require `cuInit(0)` to return zero.

The notebook has no attached input requirement and performs no P2 operation.

## Why a separate notebook

Mutating the existing P0-P2 V1 diagnostic would destroy the clean comparison
between default linker behavior and explicit-path behavior. A separate V2
probe preserves causal evidence and rollback.

## Rejected alternatives

### Global `LIBRARY_PATH` mutation

Rejected. The observed environment points `LIBRARY_PATH` at the CUDA toolkit
stub directory. Global mutation weakens attribution and risks selecting a stub.

### Global `LD_LIBRARY_PATH` mutation

Rejected. The executable carries an explicit real-driver RUNPATH and `ldd`
must prove the resolved runtime file.

### Directly link the versioned driver file

Rejected for the primary experiment. The target contract is standard `-lcuda`
resolution with an explicit real-driver search directory.

### Run P2 in the same experiment

Rejected. The next uncertainty is P1 link-path realization. Triton adds cost
and confounding before P1 is proven.

## Next gate after merge

`EXECUTE_GOVERNED_EXPLICIT_CUDA_DRIVER_LINK_PATH_PROBE_V2`
