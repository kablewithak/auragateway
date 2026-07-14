# AuraGateway Groq SDK Cache-Schema Compatibility Review

**Review ID:** `groq-sdk-cache-schema-compatibility-v1`  
**Date:** 2026-07-14  
**Mode:** Non-live compatibility review  
**Provider calls:** 0  
**Credential access:** none  
**Installed SDK:** `groq==1.5.0`  
**Adapter:** `groq-chat-completions-v1`  
**Calibration source:** `closed_billing_field_unavailable`

## Executive conclusion

The missing billing cache field is not explained by absent schema support in Groq SDK `1.5.0`, and the current evidence does not support an AuraGateway adapter extraction defect.

The bounded classification is:

```text
provider_omission_supported
```

The exact provider-side omission cause remains unresolved. This classification means the three successful observed responses omitted a field that the installed SDK and current provider documentation both support. It does not identify the internal cause of omission.

## Evidence reviewed

### Immutable live calibration

The calibration produced three successful requests with:

```text
usage present: 3 / 3
prompt_tokens_details present: 0 / 3
billing cached-token field present: 0 / 3
numeric billing-cache samples: 0
x_groq present: 3 / 3
x_groq.usage present: 0 / 3
numeric hardware-cache samples: 0
```

The terminal status remains:

```text
closed_billing_field_unavailable
```

### Installed SDK schema

The installed package is `groq==1.5.0`.

Its generated response models include:

```text
CompletionUsage.prompt_tokens_details
PromptTokensDetails.cached_tokens
ChatCompletion.x_groq
XGroq.usage
XGroqUsage.dram_cached_tokens
XGroqUsage.sram_cached_tokens
```

The `PromptTokensDetails.cached_tokens` field is an integer when the nested object exists.

### Official provider documentation

Groq's prompt-caching documentation shows billing cache usage at:

```text
usage.prompt_tokens_details.cached_tokens
```

The documentation describes zero for a cold request and a positive numeric count when matching input tokens are served from cache.

### Current adapter path

AuraGateway uses SDK field-presence metadata before serialized mapping fallback:

```text
model_fields_set
__fields_set__
serialized mapping key presence
```

This order matters because a Pydantic `model_dump()` includes default null values even when the provider did not supply those fields.

## Real SDK-object probe matrix

| Case | SDK details field | SDK cached field | Adapter details | Adapter cached field | Adapter state |
|---|---:|---:|---:|---:|---|
| Details absent | No | No | No | No | `field_absent` |
| Details explicitly null | Yes | No | Yes | No | `field_absent` |
| Cached tokens zero | Yes | Yes | Yes | Yes | `observed_zero` |
| Cached tokens positive | Yes | Yes | Yes | Yes | `observed_positive` |

Additional result:

```text
usage.prompt_tokens_details.cached_tokens = null
```

is rejected by the real SDK model because `cached_tokens` is a required integer inside `PromptTokensDetails`. The adapter's defensive mapping parser can still preserve an explicit nested null from a raw mapping if such a shape bypasses or predates the generated SDK model.

## Candidate-cause assessment

### Provider omission supported

Supported by the combined evidence:

- the field was absent on three successful live responses;
- SDK `1.5.0` models the documented field;
- real SDK objects retain numeric zero and positive values;
- the adapter preserves those values and distinguishes absence correctly;
- official documentation identifies the same field path.

### SDK schema incompatibility supported

Contradicted.

The installed SDK has the necessary response types and field-presence metadata. No upgrade is justified by this review.

### Adapter extraction defect supported

Contradicted.

The current adapter passes real SDK-object parity for absent, explicit-null, zero, and positive response shapes.

## Decisions

```text
SDK upgrade required: false
adapter change required: false
provider call authorized: false
calibration rerun authorized: false
benchmark execution authorized: false
new live authorization review permitted: true
```

## Next gate

```text
groq_cache_telemetry_reauthorization_review
```

A future authorization review should decide whether one new, separately bounded three-call calibration is worth executing under the current documented provider contract. The review must freeze exact requests, budget, stop rules, evidence fields, model identity, SDK identity, and terminal classifications before any credential is read.

## Sources

- Groq prompt caching documentation: `https://console.groq.com/docs/prompt-caching`
- Groq package registry: `https://pypi.org/project/groq/`
- Installed `groq==1.5.0` generated response models
- AuraGateway immutable calibration and closeout evidence
- AuraGateway Groq adapter and cache-capture contracts

## Non-claims

This review does not establish:

- the exact provider-internal omission cause;
- a provider cache hit or miss;
- cached-token savings;
- latency improvement;
- billing equivalence for hardware cache fields;
- comparison eligibility;
- A/B/C superiority;
- production readiness.
