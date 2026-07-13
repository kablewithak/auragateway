# ADR: Resolve Cache Telemetry Sufficiency Before the Next Benchmark

**Status:** Accepted

**Decision ID:** `cache-telemetry-before-next-benchmark-v1`

## Context

The Batch 06 diagnostic closeout established a successful 24-call controlled
execution with zero provider errors, but no cached-input-token samples were
observed.

The current Groq adapter already parses the documented billing cache field:

`usage.prompt_tokens_details.cached_tokens`

The current adapter does not retain the separate Groq hardware cache fields:

- `x_groq.usage.dram_cached_tokens`
- `x_groq.usage.sram_cached_tokens`

The exact installed Groq SDK version was not retained in execution evidence,
and successful raw responses were intentionally discarded after typed mapping.

## Decision

Do not authorize another live A/B/C benchmark yet.

First harden the adapter's successful-response telemetry boundary so future
evidence can distinguish:

- usage absent;
- prompt-token details absent;
- billing cached-token field absent;
- billing cached-token field present with zero;
- billing cached-token field present with a positive value;
- Groq hardware cache diagnostics absent or present;
- exact installed SDK version.

Billing prompt-cache tokens and hardware cache diagnostics must remain separate
semantics. DRAM or SRAM cache values may not be promoted into billing-cache
claims without explicit provider documentation establishing equivalence.

## Required implementation sequence

1. capture the exact installed Groq SDK version;
2. retain successful-response telemetry presence bits;
3. model billing cache tokens separately from hardware diagnostics;
4. add a cache-claim sufficiency gate;
5. add synthetic payload coverage;
6. prepare a separate three-call calibration authorization review.

No provider call is authorized by this review.

## Consequences

Positive:

- unknown remains unknown rather than becoming zero;
- cache claims require provider-observed billing semantics;
- SDK schema drift becomes inspectable;
- a small calibration can validate telemetry before another benchmark;
- the north-star benchmark is protected from another evidence-quality failure.

Trade-off:

- one adapter-hardening slice and one calibration-review slice are required
  before another live benchmark.

## Rejected alternatives

Treating missing cached-token telemetry as zero was rejected because absence and
a measured cache miss are different states.

Treating DRAM or SRAM hardware cache values as billing prompt-cache values was
rejected because the provider exposes them under separate names and semantics.

Using latency alone as a cache signal was rejected because the diagnostic run
was not designed or powered for a cache or latency comparison.
