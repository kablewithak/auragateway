# ADR: Option C two-stage runtime diagnostic before full Triton qualification

## Status

Accepted.

## Context

The governed CUDA 12.9 dual-T4 qualification installed the pinned runtime,
loaded the Qwen2.5-0.5B model weights in both workers, and then failed before
readiness when automatic backend selection chose FlashInfer and GNU `ld` could
not resolve `-lcuda`.

The merged deterministic-backend ADR selected explicit `TRITON_ATTN`, but
research identified a cheaper uncertainty boundary that should be tested before
the complete successor-harness and authorization cycle:

- the current Kaggle image may differ from the historical failed image;
- runtime CUDA discovery does not prove linker-visible `libcuda`;
- Triton may fail before model loading for platform or compiler reasons;
- a complete governed qualification is too expensive to use as the first basic
  linker and kernel-compilation probe.

The repository impact search matched 85 operational paths. Most are historical
records, previous reviews, or generated consumers and must not be edited
blindly.

## Decision

Adopt **Option C**, a two-stage diagnostic sequence.

### Stage 1: P0-P2 before backend implementation

P0-P2 answer platform questions only:

- **P0:** capture exact Kaggle image, GPU, driver, CUDA, compiler, linker, and
  library-path identity;
- **P1:** prove whether a minimal artifact can link with `-lcuda` without an
  unapproved filesystem mutation;
- **P2:** compile and execute one minimal Triton kernel on Tesla T4.

P0-P2 run in `KAGGLE_DIAGNOSTIC` mode with:

```text
model load = prohibited
worker start = prohibited
model requests = 0
benchmark trajectory requests = 0
network = prohibited
credentials = prohibited
customer data = prohibited
external spend = 0
```

P0-P2 do not consume the full qualification attempt.

### Stage 2: P3-P6 after merged Triton implementation

Only after P0-P2 pass may the project implement and merge explicit
`TRITON_ATTN`. The later P3-P6 diagnostic then proves:

- one canonical worker starts with explicit backend realization;
- one bounded deterministic request succeeds;
- prefix-cache telemetry and reset semantics are observable;
- two workers can coexist with correct GPU, port, process, and metric
  separation.

P3-P6 require a separate future authorization and remain prohibited in this
decision tranche.

## Failure transitions

```text
P0 failure → DIAGNOSTIC_INVALID
P1 failure → CURRENT_KAGGLE_IMAGE_LINKER_CONTRACT_FAILED
P2 failure → CURRENT_STACK_TRITON_INCOMPATIBLE
P3/P4 failure → CURRENT_VLLM_TRITON_RUNTIME_FAILED
P5 failure → RUNTIME_WORKS_BUT_PRD_OBSERVABILITY_CONTRACT_FAILED
P6 failure → SINGLE_WORKER_COMPATIBLE_DUAL_WORKER_CONTRACT_FAILED
```

## Consequences

The next implementation tranche is limited to P0-P2 diagnostic assets. It must
not modify canonical worker argv, worker hashes, runtime manifests, launchers,
or authorizations.

If P0-P2 pass, the existing deterministic-backend decision remains intact and
the project proceeds to explicit `TRITON_ATTN` implementation.

If P1 or P2 fails, the project preserves evidence and enters the bounded
compatibility-spike decision without paying for a complete successor
qualification cycle.

## Rejected alternatives

- implement Triton first and discover basic linker failure in the full run;
- rerun the failed harness unchanged;
- create a Kaggle-specific `libcuda.so` symlink;
- copy system driver libraries;
- enable silent backend fallback;
- test multiple runtime stacks in one uncontrolled notebook;
- treat P0-P2 as measured execution.

## Non-claims

This ADR does not prove the current Kaggle image, linker viability, Triton
compilation, worker startup, inference, cache reuse, reset behavior, dual-worker
readiness, measured A/B/C effect, deployment, or production readiness.
