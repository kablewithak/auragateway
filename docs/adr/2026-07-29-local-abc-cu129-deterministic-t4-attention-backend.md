# ADR: Deterministic T4 attention backend for CUDA 12.9 qualification

## Status

Approved for implementation after this review merges.

## Context

The governed T4 x2 qualification installed the exact CUDA 12.9 runtime,
loaded the Qwen2.5-0.5B snapshot, and started both vLLM 0.19.1 workers.
Automatic attention-backend selection chose FlashInfer. Both workers then
failed while linking a generated FlashInfer CUDA extension because GNU `ld`
could not resolve `-lcuda`.

The failure affected both governed workers, occurred before health readiness,
and produced zero model requests. The consumed authorization has been archived
and retired.

## Decision

The implementation tranche must make the T4 qualification backend explicit:

```text
--attention-backend TRITON_ATTN
```

The backend must be part of the canonical worker argv, CLI-capability
validation, dependency-lock evidence, worker command hashes, and generated
qualification assets.

Automatic backend selection and silent fallback to FlashInfer are prohibited
for this qualification path.

## Rationale

`TRITON_ATTN` is an explicit vLLM backend rather than a Kaggle filesystem
workaround. It avoids the observed FlashInfer JIT `-lcuda` link path while
keeping runtime behavior inspectable and deterministic.

A `libcuda.so` symlink or loader-path shim is rejected because it would bind
the harness to host filesystem details rather than the declared runtime
contract.

## Consequences

The current materialized harness is historical and cannot be reused for a
retry. After implementation merges, a new source package must be materialized,
inspected, integrated, and freshly authorized.

The wheelhouse and model snapshot are not changed by this decision unless
implementation validation exposes a separate incompatibility.

## Non-claims

This review does not prove Triton worker startup, inference, cache telemetry,
reset behavior, or full environment qualification.
