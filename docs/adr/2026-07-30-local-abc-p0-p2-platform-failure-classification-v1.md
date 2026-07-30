# ADR: Classify the corrected P0-P2 CUDA linker failure

- Status: Accepted for evidence integration
- Date: 2026-07-30
- Repository base: `b9cc4b639a2b08595497f396f1a7aa5475a4f519`
- Kaggle saved version: `339111200`
- Scope: model-free CUDA 12.9 P0-P2 platform diagnostic

## Context

The corrected launcher completed normally and returned:

```text
P0_P2_EXECUTION_LAUNCHER_COMPLETED_V2
CURRENT_KAGGLE_IMAGE_LINKER_CONTRACT_FAILED
```

P0 established that the current Kaggle image exposes two Tesla T4 devices,
driver `580.159.04`, working `nvidia-smi`, working base Torch CUDA, and a real
driver-mounted `libcuda.so` under `/usr/local/nvidia/lib64`.

P1 compiled the exact governed C source successfully. Its link command used
`-lcuda` without an explicit driver link directory. GNU ld returned:

```text
/usr/bin/ld: cannot find -lcuda: No such file or directory
```

The command selected no CUDA library. Dynamic-loader inspection and `cuInit(0)`
were not attempted. P2 was not run.

## Decision

Classify the first divergence as:

```text
CUDA_DRIVER_LIBRARY_PRESENT_RUNTIME_VISIBLE_BUT_DEFAULT_LINKER_SEARCH_PATH_UNBOUND
```

This is a refinement of the valid terminal decision
`CURRENT_KAGGLE_IMAGE_LINKER_CONTRACT_FAILED`.

Do not classify the image as generally CUDA-incompatible. The evidence proves a
default native linker-search failure, not driver absence, loader failure,
driver-initialization failure, or Triton incompatibility.

## Next diagnostic seam

Design a P1 V2 probe that:

1. admits exactly one real driver-mounted `libcuda.so`;
2. rejects every CUDA toolkit stub path;
3. links with:
   - `-L/usr/local/nvidia/lib64`
   - `-Wl,-rpath,/usr/local/nvidia/lib64`
   - `-Wl,-t`
   - `-lcuda`
4. proves that the selected link library is the real driver mount;
5. proves `ldd` resolves `libcuda.so.1` to the real driver mount;
6. requires `cuInit(0)` to return zero;
7. runs P2 only after all P1 stages pass.

The recommendation is not execution authority. A separate implementation,
review, deterministic identity rebuild, merge, source materialization,
inspection, and one bounded replay are required.

## Alternatives rejected

### Declare Kaggle incompatible

Rejected. PyTorch CUDA and the real driver mount were present. The observed
failure is narrower than platform incompatibility.

### Mutate global `LIBRARY_PATH`

Rejected for the next probe. The observed `LIBRARY_PATH` points at the toolkit
stub directory. Broad environment mutation would weaken attribution and risks
selecting a stub.

### Link directly to the versioned driver file

Retained as a fallback diagnostic. It proves direct file usability but does not
test the standard `-lcuda` build contract used by native extensions.

## Non-claims

This evidence does not prove explicit-path linking, loader resolution,
`cuInit(0)`, governed CUDA 12.9 runtime installation, Triton compilation,
vLLM worker readiness, model inference, cache telemetry, measured A/B/C,
deployment, or production readiness.
