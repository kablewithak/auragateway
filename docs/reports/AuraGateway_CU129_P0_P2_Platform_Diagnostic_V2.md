# AuraGateway CUDA 12.9 P0-P2 platform diagnostic V2

## Status

Implemented and locally validated. Not executed.

## Why V2 exists

The original diagnostic used default native `-lcuda` search. The real driver
was mounted, but the linker did not search its directory. Saved version
`339127349` proved the exact explicit real-driver contract.

V2 preserves V1 as immutable historical evidence and integrates the proven P1
boundary into a new notebook.

## Runtime sequence

```text
P0 - platform and real-driver preflight
P1 - explicit link + selected library + ELF + ldd + cuInit(0)
P2 - governed offline CUDA 12.9 install + one Triton vector-add kernel
```

The sequence stops at the first failure.

## P1 invariants

```text
exact C source SHA-256
one syntax compile
one explicit link
one real libcuda selected
CUDA toolkit stub absent
ELF NEEDED=libcuda.so.1
ELF RUNPATH=/usr/local/nvidia/lib64
ldd resolves the real driver mount
cuInit(0) returns zero
global linker environment unchanged
```

## P2 invariants

```text
exactly one governed wheelhouse input
all control and manifest hashes validated
176 wheel entries
one offline target installation
Torch 2.10.0+cu129
Torch CUDA build 12.9
Torch and Triton loaded from the target runtime
one T4 exposed to the child process
one exact vector-add result
no model, worker or request
```

## Failure taxonomy

P1 distinguishes source, compile, explicit link, selected-library, ELF,
dynamic-loader, driver-initialization and environment-integrity failures.

P2 distinguishes wheelhouse, installation, runtime-import, kernel and
environment-integrity failures.

## Privacy and safety

No customer data, credentials, secrets, external network calls or raw
environment dump is permitted. Only allowlisted environment values and bounded
command output are recorded.

## Commercial translation

This is an **AI System Evaluation Audit** proof asset. It demonstrates that a
generic "GPU incompatibility" can be decomposed into deterministic platform,
linker, loader, runtime and kernel gates before expensive model execution.

## Next gate after merge

`EXECUTE_GOVERNED_P0_P2_PLATFORM_DIAGNOSTIC_V2`
