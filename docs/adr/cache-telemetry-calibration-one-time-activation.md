# ADR: Activate One-Time Groq Cache Telemetry Calibration

**Status:** Accepted

**Decision ID:** `cache-telemetry-calibration-one-time-activation-v1`

## Context

The calibration authorization review froze a three-call cold/warm/warm
sequence but intentionally exposed no live execution command.

The provider adapter now retains:

- exact installed Groq SDK version;
- billing cache field presence and value;
- DRAM and SRAM hardware cache diagnostics separately;
- protected provider output outside public evidence.

The next engineering requirement is a one-time runtime harness that can execute
the reviewed calibration without expanding it into a benchmark.

## Decision

Create an active authorization and execution harness for exactly three calls.

The runtime must:

1. bind the exact inactive review assets and protected prompt bundle;
2. require an exact authorization ID;
3. require the exact confirmation phrase;
4. require `GROQ_API_KEY` only for live preflight and execution;
5. enforce offsets of 0, 10, and 20 seconds;
6. reuse one exact provider request for all three calls;
7. stop on the first provider or telemetry failure;
8. write one public journal record for every planned attempt;
9. retain provider output only beneath ignored `.local` storage;
10. block rerun and resume if any execution evidence exists.

## Outcome taxonomy

Execution must classify exactly one outcome:

- `telemetry_observed_with_cache_hit`;
- `telemetry_observed_without_cache_hit`;
- `billing_cache_field_unavailable`;
- `calibration_execution_failed`.

A cache-usage observation is limited to the three calibration calls.

No cache-savings, latency, benchmark, or production-readiness claim is
authorized by this calibration.

## Cost and call ceiling

- maximum provider calls: 3;
- planned maximum cost: 600 micro-USD;
- authorization ceiling: 1,000 micro-USD;
- retries: forbidden;
- resume: forbidden.

The cost values are harness estimates, not provider billing records.

## Consequences

Positive:

- the missing-versus-zero telemetry question can be resolved with three calls;
- live evidence is one-time and hash-verifiable;
- protected output remains outside Git;
- the next handover boundary can be based on empirical evidence.

Trade-off:

- execution must occur in a later dedicated evidence branch;
- interrupted execution cannot resume and requires a new reviewed
  authorization.
