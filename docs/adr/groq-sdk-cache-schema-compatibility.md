# ADR: Close Groq SDK Cache-Schema Review Without an SDK Upgrade

## Status

Accepted on 2026-07-14.

## Context

The closed three-call Groq calibration succeeded at the provider-call boundary but returned no numeric billing cache samples. The billing field `usage.prompt_tokens_details.cached_tokens` was absent on all three successful responses. The top-level `x_groq` object was present, while `x_groq.usage` and its DRAM/SRAM cache fields were absent.

The project had to distinguish four possible explanations:

1. the provider omitted the documented field;
2. Groq SDK `1.5.0` did not model or preserve the field;
3. AuraGateway's adapter lost the field or fabricated absence;
4. the available evidence could not distinguish the boundary.

A live rerun was prohibited. The review therefore used immutable calibration evidence, the installed SDK schema, synthetic real-SDK response objects, the existing adapter, and current official documentation.

## Decision

Close the compatibility review with this bounded classification:

```text
primary classification: provider_omission_supported
exact provider omission cause: unresolved
SDK schema incompatibility: contradicted
adapter extraction defect: contradicted
SDK upgrade required: no
adapter change required: no
provider call authorized: no
```

Groq SDK `1.5.0` explicitly models:

```text
usage.prompt_tokens_details.cached_tokens
x_groq.usage.dram_cached_tokens
x_groq.usage.sram_cached_tokens
```

Real `ChatCompletion` objects prove that `model_fields_set` distinguishes an omitted `prompt_tokens_details` field from an explicitly null field even though `model_dump()` includes default null values. AuraGateway's adapter checks SDK field-presence metadata before falling back to serialized mappings, so omitted SDK defaults do not become fabricated field presence.

The SDK accepts numeric zero and positive `cached_tokens` values. It rejects a nested null `cached_tokens` value because the generated SDK field is a required integer when `prompt_tokens_details` exists. AuraGateway's mapping parser remains intentionally more defensive and can still preserve a provider mapping containing an explicit nested null as `FIELD_NULL`.

## Consequences

### Positive

- No speculative SDK upgrade is introduced.
- The existing adapter remains unchanged because real SDK-object parity passes.
- Missing telemetry remains unavailable rather than zero.
- The compatibility result is reproducible without credentials or provider calls.
- The next decision can focus on whether a separately reviewed calibration reauthorization is justified.

### Negative

- The exact provider-side reason for omission remains unknown.
- This review does not prove that a future call will include the billing field.
- It does not establish a cache hit, cache miss, saving, latency improvement, or A/B/C result.

## Rejected alternatives

### Upgrade the Groq SDK

Rejected. Version `1.5.0` is the current reviewed release and already contains the required schema. An upgrade would add dependency and fingerprint churn without evidence that schema support is missing.

### Change the adapter extraction path

Rejected. Real SDK response objects for absent, explicit-null, zero, and positive shapes pass through the current adapter with the expected presence semantics.

### Rerun the provider calibration immediately

Rejected. The consumed authorization remains terminal. A new live run requires a separate authorization review with a new bounded purpose, budget, schedule, stop rules, and evidence plan.

## Next gate

```text
groq_cache_telemetry_reauthorization_review
```

This gate may review a new three-call calibration. It does not itself authorize execution.
