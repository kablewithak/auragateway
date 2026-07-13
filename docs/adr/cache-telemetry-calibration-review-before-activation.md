# ADR: Review Cache Telemetry Calibration Before Activation

**Status:** Accepted

**Decision ID:** `cache-telemetry-calibration-review-before-activation-v1`

## Context

The Groq cache telemetry capture boundary is now production-shaped enough to
distinguish:

- billing cache field absent;
- billing cache field null;
- measured zero cached tokens;
- measured positive cached tokens;
- DRAM and SRAM hardware cache diagnostics;
- exact installed Groq SDK version.

The next uncertainty is empirical: whether the provider exposes the billing
cache field and whether an exact repeated request produces a measured cache
observation under the current account, model, SDK, and runtime boundary.

A full A/B/C benchmark would be the wrong next move. It would spend more calls
before confirming that the provider telemetry needed for a cache claim is
actually observable.

## Decision

Freeze an inactive authorization review for one three-call calibration:

1. cold request;
2. exact request repeat;
3. second exact request repeat.

The implementation branch may materialize and verify the synthetic prompt
bundle, validate the review, and reproduce a metadata-only dry run.

It may not:

- read `GROQ_API_KEY`;
- instantiate the Groq client;
- perform a provider call;
- create an active authorization;
- expose a live execution command;
- authorize retries or resume;
- authorize a benchmark.

## Prompt shape

The protected prompt contains:

- an 8,192-byte synthetic static system prefix;
- a 256-byte synthetic user request;
- 8,448 total prompt bytes;
- a conservative 2,112-token estimate.

Groq documents model-dependent cacheable minimums ranging from 128 to 1,024
tokens. The frozen estimate therefore leaves a 1,088-token margin above the
documented upper bound.

All three provider-visible request payloads must be byte-identical.

## Schedule and budget

The planned offsets are:

- 0 seconds;
- 10 seconds;
- 20 seconds.

The calibration permits at most three future provider calls, with no retry and
no resume.

The planning estimate is 600 micro-USD with a 1,000 micro-USD authorization
ceiling. These values are bounded planning evidence, not a provider invoice.

## Outcome taxonomy

The future activation must classify exactly one outcome:

- telemetry observed with a cache hit;
- telemetry observed without a cache hit;
- billing cache field unavailable;
- calibration execution failed.

A successful calibration may support a provider-cache observation only for
these three calls. It does not authorize benchmark, latency, quality, routing,
or production-readiness claims.

## Consequences

Positive:

- the cheapest useful live check comes before another benchmark;
- exact request identity is hash-bound;
- provider-field absence remains distinct from measured zero;
- no failed or ambiguous call can be retried or hidden;
- activation remains a separate deliberate decision.

Trade-off:

- one additional activation slice is required before the three live calls.
