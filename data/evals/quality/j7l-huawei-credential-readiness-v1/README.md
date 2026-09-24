# J7L Huawei Credential Readiness V1

Status: **review-ready and inactive**.

This boundary exists because the first governed GLM-5.2 named-tool qualification reached the
Huawei model-catalog authentication boundary and received HTTP 401 before any model inference.
The failed qualification authorization is consumed and remains nonreusable.

## Purpose

The readiness boundary isolates one question before any fresh named-tool qualification authority:

> Can a separately authorized `HUAWEI_MAAS_API_KEY` authenticate against the exact Huawei
> ModelArts MaaS catalog boundary and observe the exact `glm-5.2` model ID?

That question is intentionally narrower than model inference readiness.

## Frozen provider boundary

- provider: `huawei_modelarts_maas`
- region: `ap-southeast-1`
- model: `glm-5.2`
- catalog endpoint: `https://api-ap-southeast-1.modelarts-maas.com/v2/models`
- credential environment variable: `HUAWEI_MAAS_API_KEY`
- HTTP backend: `urllib.request`

## Implementation

The deterministic classification core remains unchanged:

`src/auragateway/local_abc/j7l_huawei_credential_readiness_v1.py`

SHA-256:

`aa8f5f88d44112b8553b0b0945496762354828d1dab3e66a61e9b6d1ecf90a86`

Focused classifier tests:

`tests/unit/local_abc/test_j7l_huawei_credential_readiness_v1.py`

SHA-256:

`a2fbdd05d13414a83e8f227c4fd8ad804f1871fbb2821964bab08a8a63198cce`

The activation candidate adds the real one-shot Huawei catalog adapter and dormant single-use
execution machinery:

`src/auragateway/local_abc/j7l_huawei_credential_readiness_activation_v1.py`

SHA-256:

`5b7d9db850cc864b89bc169e07d448c24565f9d56bf171f2fc902a31f1e1a091`

Focused activation tests:

`tests/unit/local_abc/test_j7l_huawei_credential_readiness_activation_v1.py`

SHA-256:

`62319fbc399d976bab1df603600e457a10ba7bec5a64c79cfc1fce72af6e2f95`

The real adapter uses default TLS verification, blocks redirects, performs no retries, bounds
successful response reads, and does not read or persist HTTP error bodies. HTTP 401, 403, 429,
and 5xx responses remain available to the existing deterministic classifier as distinct states.

## Current authority

The implementation is deliberately non-live in this tranche.

- provider calls authorized: false
- credential access authorized: false
- network access authorized: false
- execution command available under current authority: false
- authorization artifact present: false

The dormant execution path requires a future, separately reviewed authorization artifact before
it can read the credential or make a network request.

## Future single-use request ceiling

A later authorization may permit at most:

- one authenticated catalog GET;
- zero model inference requests;
- zero automatic retries;
- zero resume or rerun under the same authorization;
- zero J7L reference requests;
- zero Jev requests;
- zero binding actions;
- R0 external spend.

The authorization is consumed immediately before the first provider network attempt. A missing
credential does not consume authority because no network attempt can occur.

## Classification contract

- HTTP 200 with exactly one `glm-5.2` catalog entry -> `READY`
- HTTP 401 -> `AUTHENTICATION_FAILED`
- HTTP 403 -> `ENTITLEMENT_DENIED`
- HTTP 429 -> `RATE_LIMITED`
- HTTP 5xx -> `PROVIDER_UNAVAILABLE`
- transport failure -> `TRANSPORT_FAILED`
- malformed successful catalog -> `CATALOG_INVALID`
- successful catalog without exact `glm-5.2` -> `MODEL_NOT_PRESENT`

## Evidence and privacy boundary

The readiness result never persists:

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

It does not establish chat-completion entitlement, successful GLM-5.2 inference, named-tool
transport, disabled-thinking behavior, usage accounting, reference-judge quality, independent
zero-spend proof, or any downstream execution authority.

## Next gate

`AUTHORIZE_J7L_HUAWEI_CREDENTIAL_READINESS_ONCE_V1`

No Huawei request is performed by this implementation tranche.
