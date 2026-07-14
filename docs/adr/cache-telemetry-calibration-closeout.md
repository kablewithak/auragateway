# ADR: Close the Groq Cache Telemetry Calibration as Billing-Field Unavailable

**Status:** Accepted

**Decision ID:** `groq-cache-telemetry-calibration-closeout-v1`

## Context

The one-time Groq cache telemetry calibration executed exactly three identical
provider requests at offsets of 0, 10, and 20 seconds.

All three provider calls succeeded. The public evidence verified and the
authorization is consumed.

Every successful response retained:

- installed Groq SDK version `1.5.0`;
- normal usage presence;
- `x_groq` presence;
- content-free token and duration telemetry.

Every successful response also showed:

- `prompt_tokens_details` absent;
- billing cached-token field absent;
- `x_groq.usage` absent;
- DRAM and SRAM cache fields absent.

The missing billing field is unavailable evidence, not a measured zero.

## Decision

Close the calibration with status:

`closed_billing_field_unavailable`

Retain the successful-response telemetry capture and all one-time execution
controls.

Do not:

- rerun or resume the calibration;
- mutate execution evidence;
- change prompt construction or routing from this result;
- restart the A/B/C benchmark;
- claim provider cache usage, savings, latency improvement, or comparison
  superiority.

## Next gate

The next gate is:

`groq_sdk_cache_schema_compatibility_review`

That review must determine whether the observed field absence is attributable
to SDK response-model compatibility, provider response omission, or another
provider-boundary condition.

It must begin with non-live schema and compatibility inspection. A provider
rerun requires a new explicit review and authorization.

## Consequences

Positive:

- the calibration arc ends with a deterministic evidence boundary;
- missing telemetry remains distinct from a cache miss;
- evidence selection through rerun is prevented;
- the next investigation is narrow and testable.

Trade-off:

- the north-star A/B/C benchmark remains blocked;
- provider cache usage and savings remain unmeasured;
- the exact unavailability cause remains unresolved.
