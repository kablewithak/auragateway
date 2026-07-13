# ADR: Do Not Apply a Request-Shape Fix After Batch 06 Nonreproduction

**Status:** Accepted
**Decision ID:** `batch-06-nonreproduction-no-request-shape-fix-v1`

## Context

Batch 06 ended with one verified provider request rejection. A later controlled diagnostic executed 24 provider calls across order-reversal and spacing cells.

All 24 calls succeeded. No request rejection, provider error, or skipped attempt occurred.

The diagnostic also proved matched B/C provider-request identities at the serialized provider boundary. Cached-input-token telemetry was unavailable.

## Decision

Do not change:

- request construction;
- prompt byte targets;
- conversation-history construction;
- condition B routing;
- condition C cache-affinity routing.

Retain the request-rejection taxonomy and privacy-safe diagnostic evidence introduced after Batch 06.

## Rationale

The controlled execution strongly contradicts a deterministic request defect and does not reveal a reproducible harness divergence.

A request-shape or routing change would therefore solve no demonstrated defect while increasing regression risk and contaminating the next A/B/C baseline.

The best-supported explanation is a transient or hidden provider/backend event. Provider-internal causation was not observed and is not claimed.

## Consequences

Positive:

- the next benchmark preserves the current harness baseline;
- no speculative fix is introduced;
- the original failure and successful diagnostic remain separately queryable;
- future request rejections retain stronger safe diagnostics.

Trade-off:

- the exact Batch 06 provider-side cause remains unknown;
- another isolated rejection may require a new authorization and evidence set;
- cache claims remain blocked until telemetry sufficiency is resolved.

## Next gate

Run a cache-telemetry sufficiency review before authorizing another accepted A/B/C benchmark.
