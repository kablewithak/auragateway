# ADR: Accept P3-P6 Runtime Diagnostic Failure V3

## Status

Accepted for repository implementation after Kaggle saved version `339943910`.

## Context

The governed V3 run used one T4 x2 Kaggle session with Internet disabled.
Offline target-runtime installation and the nested process-tree import-closure
gate passed. The first worker loaded the exact Qwen snapshot, became healthy,
and exposed the exact served-model inventory.

The worker emitted:

```text
Using AttentionBackendEnum.TRITON_ATTN backend.
```

The V3 classifier required both `triton_attn` and the separate spaced phrase
`attention backend` anywhere in the combined worker logs. The pinned vLLM
message contains `AttentionBackendEnum` as one token, so the classifier
reported `P3_P6_EXPLICIT_BACKEND_NOT_REALIZED` even though startup backend
selection had succeeded.

## Decision

Preserve the exact authorization, FAILED consumption receipt, intake archive,
runtime archive, queryable runtime members, terminal log, source authorities,
limitations, and third-party backend-selection authority.

Accept the lifecycle outcome as `FAILED` and classify the reported backend
failure as `QUARANTINED_INVALID_DIAGNOSTIC`.

Do not rewrite the run as a successful P3 execution. Startup readiness,
served-model inventory, and TRITON_ATTN selection are established through the
exact control flow and retained trace. Formal composite P3 acceptance and
request-level attention execution remain unestablished.

## Consequences

V4 must harden the P3 runtime evidence contract. It must use an exact
single-line backend marker, reject CLI argument echo, finalize capture before
terminal serialization, retain matched-line identity, record worker and GPU
identity, prove teardown, and bind the executed notebook or code-cell identity.

V3 may not be replayed unchanged.
