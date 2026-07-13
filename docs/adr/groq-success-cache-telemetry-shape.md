# ADR: Retain a Privacy-Safe Groq Success Cache Telemetry Shape

**Status:** Accepted

**Decision ID:** `groq-success-cache-telemetry-shape-v1`

## Context

The Batch 06 diagnostic completed 24 provider calls successfully but retained no
cached-input-token samples.

The current adapter parses the documented billing cache field, but it does not
retain enough successful-response shape evidence to distinguish:

- field absent;
- field present with null;
- field present with measured zero;
- field present with a positive value;
- hardware cache diagnostics present under `x_groq`;
- exact installed Groq SDK version.

Missing evidence cannot be represented as a measured cache miss.

## Decision

Add a separate successful-response telemetry shape to `ProviderCall`.

The shape retains only:

- fixture and model identity;
- adapter and capture contract versions;
- exact installed Groq SDK version;
- field-presence booleans;
- bounded non-negative cache-token values.

The shape excludes prompts, messages, outputs, response identifiers, headers,
credentials, and raw provider payloads.

Billing prompt-cache tokens remain separate from Groq DRAM and SRAM hardware
cache diagnostics.

## Sufficiency rule

Provider cache usage is permitted only when:

- the billing cache field is present;
- its value is numeric, including measured zero;
- provider input tokens are present and positive;
- cached tokens do not exceed input tokens;
- provider, model, and fixture identities match.

Hardware cache values cannot satisfy the billing-cache gate.

Provider cache savings additionally requires versioned pricing evidence.

## Calibration boundary

This slice prepares an inactive three-call calibration draft:

1. cold request;
2. exact request repeat;
3. second exact request repeat.

The draft authorizes no provider call, retry, resume, calibration, or benchmark.

## Consequences

Positive:

- absent and measured zero become distinct states;
- future SDK schema drift is inspectable;
- hardware and billing semantics remain separated;
- later cache claims become machine-gated;
- no raw successful response needs to be retained.

Trade-off:

- `ProviderCall` carries one optional additive metadata field;
- a separately reviewed calibration is still required before another benchmark.
