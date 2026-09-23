# J7L Huawei Credential Readiness V1

Status: **review-ready and inactive**.

This tranche exists because the first governed GLM-5.2 named-tool qualification reached the authenticated Huawei model-catalog boundary and received HTTP 401 before any model inference request was attempted.

The failed qualification authorization is consumed and is not reusable. This readiness design does not modify, resume, or rerun that execution.

## Purpose

The readiness boundary isolates one question before any future named-tool qualification authority is considered:

> Can the current `HUAWEI_MAAS_API_KEY` authenticate against the exact Huawei ModelArts MaaS catalog boundary and observe the exact `glm-5.2` model ID?

That question is intentionally narrower than model inference readiness.

## Frozen provider boundary

- provider: `huawei_modelarts_maas`
- region: `ap-southeast-1`
- model: `glm-5.2`
- catalog endpoint: `https://api-ap-southeast-1.modelarts-maas.com/v2/models`
- credential environment variable: `HUAWEI_MAAS_API_KEY`

## Implementation identity

Classification source:

`src/auragateway/local_abc/j7l_huawei_credential_readiness_v1.py`

SHA-256:

`aa8f5f88d44112b8553b0b0945496762354828d1dab3e66a61e9b6d1ecf90a86`

Focused tests:

`tests/unit/local_abc/test_j7l_huawei_credential_readiness_v1.py`

SHA-256:

`a2fbdd05d13414a83e8f227c4fd8ad804f1871fbb2821964bab08a8a63198cce`

Base repository commit:

`98d46c0396de94b99b3c2ceb93b9809474d9e2cc`

The current implementation is classification-core-only. It uses an injected catalog client and therefore performs no real provider traffic by itself.

A real network adapter and single-use activation boundary are not yet implemented.

## Planned future live request ceiling

A later authorization may permit at most:

- one authenticated catalog GET;
- zero model inference requests;
- zero automatic retries;
- zero J7L reference requests;
- zero Jev requests;
- zero binding actions;
- R0 external spend.

This document does not grant that authority.

## Classification contract

- HTTP 200 with exactly one `glm-5.2` catalog entry -> `READY`
- HTTP 401 -> `AUTHENTICATION_FAILED`
- HTTP 403 -> `ENTITLEMENT_DENIED`
- HTTP 429 -> `RATE_LIMITED`
- HTTP 5xx -> `PROVIDER_UNAVAILABLE`
- transport failure -> `TRANSPORT_FAILED`
- malformed successful catalog -> `CATALOG_INVALID`
- successful catalog without exact `glm-5.2` -> `MODEL_NOT_PRESENT`

Authentication failure, entitlement denial, and rate limiting remain distinct states.

## Evidence and privacy boundary

The readiness result must never persist:

- the API key;
- the Authorization header;
- raw provider error bodies;
- J7L case content;
- Jev content;
- frozen reference answers.

Only metadata-safe readiness evidence may cross the public evidence boundary.

## Claim boundary

A future `READY` observation may establish only that, at the observed time:

1. the supplied credential authenticated at the catalog boundary; and
2. the exact `glm-5.2` model ID was visible in that catalog response.

It does not establish chat-completion entitlement, successful GLM-5.2 inference, named-tool transport, disabled-thinking behavior, usage accounting, reference-judge quality, independent zero-spend proof, or any downstream execution authority.

## Current authority

- provider calls authorized: false
- credential access authorized: false
- network access authorized: false
- execution command available: false

## Next gate

`IMPLEMENT_J7L_HUAWEI_CREDENTIAL_READINESS_ACTIVATION_V1`
