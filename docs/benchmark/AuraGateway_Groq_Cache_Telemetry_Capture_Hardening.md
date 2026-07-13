# AuraGateway Groq Cache Telemetry Capture Hardening

**Hardening ID:** `groq-cache-telemetry-hardening-v1`

**Status:** `implementation_ready`

**Provider calls performed:** No

**Calibration authorized:** No

**Next gate:** `cache_telemetry_calibration_authorization_review`

## Purpose

This slice closes the successful-response observability gap identified by the
cache telemetry sufficiency review.

It does not attempt another provider calibration or A/B/C benchmark.

## Added capture boundary

Every successful Groq call may now retain a content-free telemetry shape with:

- exact installed Groq SDK version;
- usage presence;
- prompt-token-details presence;
- billing cached-token field presence;
- billing cached-token value;
- `x_groq` presence;
- `x_groq.usage` presence;
- DRAM cached-token field presence and value;
- SRAM cached-token field presence and value.

The provider request and protected output boundaries remain unchanged.

## State semantics

Billing cache telemetry has four explicit states:

- `field_absent`
- `field_null`
- `observed_zero`
- `observed_positive`

Only the final two states are measured observations.

A field-present zero is a measured cache miss. A missing or null field remains
unavailable evidence.

## Claim gate

Provider cache usage requires:

- explicit billing field presence;
- numeric cached tokens;
- positive provider input-token denominator;
- cached tokens not exceeding total input tokens;
- matching provider, model, and fixture identities.

Provider cache savings additionally requires versioned pricing evidence.

DRAM and SRAM hardware cache diagnostics cannot satisfy the billing gate.

## Deterministic cases

The committed synthetic case set covers:

- billing field absent;
- billing field null;
- measured zero;
- measured positive;
- cached tokens exceeding input tokens;
- hardware-only cache signals;
- missing input-token denominator.

## Prepared calibration

The inactive draft contains exactly three requests:

1. cold;
2. warm repeat one;
3. warm repeat two.

It forbids:

- provider calls in this slice;
- retries;
- resume;
- calibration execution;
- benchmark execution.

## Privacy boundary

The success shape does not retain:

- raw prompts;
- raw messages;
- raw outputs;
- raw responses;
- response IDs;
- headers;
- credentials;
- provider error messages.

## Acceptance

- all six reviewed hardening actions completed;
- cache field presence is explicit;
- installed SDK version capture is available;
- billing and hardware semantics are separate;
- cache sufficiency is machine-enforced;
- deterministic negative controls pass;
- calibration remains inactive;
- no provider credential is read;
- no provider call is made.

## Commercial proof

This is a concrete AI System Evaluation Audit artifact.

It demonstrates that the system distinguishes missing evidence from a
favorable zero and prevents provider-specific hardware diagnostics from being
misrepresented as billing-cache savings.
