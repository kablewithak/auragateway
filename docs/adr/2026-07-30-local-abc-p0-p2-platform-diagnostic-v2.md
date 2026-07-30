# ADR: Integrate the accepted explicit driver-link contract into P0-P2 V2

- Status: Accepted for implementation
- Date: 2026-07-30
- Source main: `fe297a6f1aeed04119452552874dab22bfe01dee`
- Accepted probe saved version: `339127349`

## Context

P0-P2 diagnostic V1 failed at its default `-lcuda` link. The independent
explicit-link probe then proved that the current Kaggle image can compile,
link, dynamically resolve and initialize the real CUDA driver when the native
link command includes:

```text
-L/usr/local/nvidia/lib64
-Wl,-rpath,/usr/local/nvidia/lib64
-Wl,-t
-lcuda
```

The accepted evidence also proves that global linker-environment mutation and
CUDA toolkit stub linking are unnecessary.

## Decision

Create a separate P0-P2 platform diagnostic V2. Do not edit or replace V1.

V2 performs:

```text
P0: exact platform, dual-T4 and real-driver preflight
P1: exact source, explicit real-driver link, link trace, ELF, ldd, cuInit(0)
P2: one hash-locked offline CUDA 12.9 install and one Triton vector-add kernel
```

P2 runs only after P0 and P1 pass.

For Triton's internally generated native compilation, V2 uses a child-process
environment rather than mutating the notebook process:

```text
LIBRARY_PATH=/usr/local/nvidia/lib64
LDFLAGS=-L/usr/local/nvidia/lib64 -Wl,-rpath,/usr/local/nvidia/lib64
LD_LIBRARY_PATH=<target NVIDIA libs>:/usr/local/nvidia/lib64:<inherited>
```

This is a bounded command-local realization. The global environment is checked
before and after P1 and P2.

## Rejected alternatives

- mutate diagnostic V1;
- globally rewrite `LIBRARY_PATH`;
- globally rewrite `LD_LIBRARY_PATH`;
- link the CUDA toolkit stub;
- create or copy `libcuda` symlinks;
- jump directly to vLLM, model, worker or A/B/C execution;
- retry hidden alternative commands.

## Execution budget

```text
Kaggle sessions: 1
P0 attempts: 1
P1 source/compile/link/ELF/ldd/cuInit attempts: 1 each
offline runtime installs: 1
Triton kernel attempts: 1
model loads, workers, requests, network calls: 0
```

## Consequences

A V2 pass proves the selected CUDA 12.9 runtime can execute one minimal Triton
primitive on one T4 under the accepted driver-link contract.

A V2 failure remains useful evidence because it identifies the first boundary
after the default linker defect was removed.

## Next gate after merge

`EXECUTE_GOVERNED_P0_P2_PLATFORM_DIAGNOSTIC_V2`

## Non-claims

This implementation does not establish P2 success, vLLM readiness, model
inference, A/B/C behavior, deployment or production readiness.
