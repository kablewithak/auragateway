# ADR: Implement bounded worker-startup diagnostics before qualification retry

- **Status:** Accepted and implemented locally
- **Date:** 2026-07-22
- **Review merge:** `997efb4aacf998567a3d92e7202a0054bf473ca4`
- **Decision:** `IMPLEMENT_DIAGNOSTICS_THEN_REMATERIALIZE`

## Context

CUDA 12.9 environment-qualification Attempt 5 reached worker startup but retained only a
generic readiness timeout. The active runtime adapter discarded both worker streams and did
not retain process exit state or readiness history.

The active Kaggle harness remains the consumed `426f57d` lineage. Changing executable
adapter and launcher code therefore cannot be promoted directly into its manifest identity.

## Decision

Implement one bounded diagnostic boundary that:

1. drains each worker stream into byte-bounded isolated workspace files;
2. retains worker identity, GPU assignment, loopback endpoint, command SHA-256, process state,
   and bounded readiness-poll history;
3. sanitizes and byte-bounds stream tails before canonical JSON serialization;
4. writes one typed diagnostic atomically before raising the terminal startup error;
5. embeds the exact diagnostic JSON in the launcher failure ZIP;
6. preserves zero hidden retries, zero replacement, and zero fallback;
7. regenerates the governed launcher deterministically;
8. provides a post-merge source-package and CPU-only materializer toolchain.

## Authority boundary

The current manifest and materialization record remain bound to the historical `426f57d`
harness until a new post-merge source package is materialized and inspected.

The previously implemented authorization issuer remains bound to the historical adapter and
launcher identities. It is deliberately unusable after this implementation and must not be
updated until the rematerialized harness evidence is integrated.

## Privacy and security

Diagnostics exclude raw environments, authorization payloads, raw command argv, model
content, credentials, customer data, and hosted-provider inputs. Common secret shapes,
absolute Kaggle paths, Windows paths, and message content are redacted before persistence.

Each stream retains at most 32 KiB. The complete diagnostic is limited to 256 KiB. The
launcher ZIP remains limited to 2 MiB.

## Consequences

A new qualification retry is still unauthorized. After merge, the source-package toolchain
must run on clean synchronized `main`, followed by one CPU-only harness materialization and
one metadata-only inspection. Active manifest identities may move only from consumed
inspection evidence.

## Non-claims

This implementation does not identify the Attempt 5 root cause, prove worker startup, prove
model fit, qualify cache telemetry, authorize measured A/B/C, or establish production
readiness.
