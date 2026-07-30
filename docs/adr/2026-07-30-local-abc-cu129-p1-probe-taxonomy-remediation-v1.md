# ADR: CUDA 12.9 P1 Probe Source and Failure Taxonomy Remediation V1

## Status

Accepted for local implementation. Kaggle replay is blocked until merge and corrected
source materialization.

## Context

Kaggle saved version `338921762` completed the launcher but reported
`CURRENT_KAGGLE_IMAGE_LINKER_CONTRACT_FAILED`. The preserved platform evidence
proved that the generated C file contained literal backslash-`n` characters.
The C compiler rejected malformed source before a valid CUDA link attempt.

The prior result therefore does not establish a platform linker failure.

## Decision

Repair the diagnostic at the harness boundary:

1. Materialize one exact byte constant for the P1 C source.
2. Verify SHA-256, two LF bytes, and absence of literal backslash-`n`.
3. Compile the source to an object with strict C11 warnings.
4. Link the object against `-lcuda`.
5. Resolve `libcuda.so.1` with `ldd`.
6. Execute the probe and classify `cuInit(0)` separately.
7. Propagate the exact P1 decision to the terminal summary.
8. Rebuild every downstream deterministic identity.

## Failure taxonomy

```text
source byte failure        -> DIAGNOSTIC_INVALID
C syntax/object failure    -> DIAGNOSTIC_INVALID
-lcuda link failure        -> CURRENT_KAGGLE_IMAGE_LINKER_CONTRACT_FAILED
loader resolution failure  -> CURRENT_KAGGLE_IMAGE_LINKER_CONTRACT_FAILED
cuInit nonzero             -> CURRENT_KAGGLE_IMAGE_DRIVER_INITIALIZATION_FAILED
all stages pass            -> CUDA_DRIVER_LINKER_CONTRACT_PASSED
```

## Consequences

The corrected replay can distinguish harness defects, linker failures, dynamic
loader failures, and driver initialization failures. P2 remains stop-on-first-failure.

The source materializer and execution launcher identities change because the
diagnostic notebook, request, and implementation record changed.

## Safety

No GPU, Kaggle, model, worker, network, credential, customer-data, or benchmark
execution is performed by this repository change.

## Non-claims

This ADR does not establish CUDA linker viability, `cuInit` success, Triton
compatibility, model serving, environment qualification, or production readiness.
