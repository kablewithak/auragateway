# AuraGateway Groq Failure Diagnostic Boundary

## Status

```text
slice=phase-7-groq-failure-diagnostic-hardening
batch_04_authorization=blocked
live_provider_execution=not_permitted_by_this_slice
customer_data=prohibited
```

## Purpose

Batch 03 proved that the existing Groq adapter collapsed materially different provider and SDK failures
into `PROVIDER_RESPONSE_INVALID` without retaining enough safe metadata to recover the cause.

This slice hardens the provider boundary before any Batch 04 authorization.

It does not authorize another live run.

## Diagnostic contract

Provider failures may be classified as:

```text
request_rejected
response_schema_invalid
assistant_content_missing
timeout
rate_limited
authentication_failed
permission_denied
model_unavailable
connection_failed
provider_unavailable
unknown_provider_exception
```

The protected local diagnostic record may retain only:

```text
schema_version
provider
model_alias
request_id_sha256
family
exception_class_allowlisted
http_status_code
provider_error_type_allowlisted
provider_error_code_allowlisted
provider_error_param_allowlisted
provider_request_id_sha256
retryable
mapped_provider_error_code
```

## Privacy boundary

The diagnostic sink must never retain:

```text
raw exception message
raw provider error body
raw prompt
raw user content
raw retrieved document text
raw model output
provider request ID in plaintext
credentials
secrets
arbitrary headers
```

Exception classes, provider error types, error codes, and parameter names use explicit allowlists.
Unknown or unapproved values become `null`.

Provider request IDs are hashed before persistence.

## Runtime behavior

`GroqProviderAdapter` accepts an optional protected diagnostic path.

When configured:

- every classified failure appends one JSONL diagnostic record;
- the file is flushed and fsynced;
- successful calls write no diagnostic record;
- diagnostic persistence failure converts the original provider failure into a non-retryable ambiguous
  evidence failure.

When no diagnostic path is configured, existing adapter behavior remains compatible.

The public provider-neutral error mapping remains unchanged.

## Regression coverage

The slice proves:

- HTTP 400 request rejection is separate from response-schema failure;
- rate limiting retains retryability without raw quota text;
- unknown exception classes and messages are not retained;
- provider metadata outside explicit allowlists is discarded;
- malformed SDK response objects are classified separately;
- missing assistant content remains an ambiguous response;
- provider request identifiers are hashed;
- diagnostic write failure blocks execution;
- successful calls do not create failure records;
- the diagnostic contract rejects extra raw fields and unsafe tokens.

## Next gate

After this slice merges, Batch 04 still requires a separate authorization slice that:

1. wires a Batch 04 diagnostic path under `.local/benchmark/live-development-v4/`;
2. freezes the Batch 04 runtime policy and authorization;
3. preserves all Batch 01–03 evidence unchanged;
4. validates the diagnostic sink before loading credentials;
5. runs one fresh development-only A/B/C triplet;
6. stops for receipt and diagnostic review before any commit.

No measured, held-out, or full-benchmark execution is authorized here.
