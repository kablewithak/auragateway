# AuraGateway Provider Request-Rejection Hardening

**Slice:** Non-live diagnostic hardening after Batch 06  
**Branch:** `fix/provider-request-rejection-diagnostics`  
**Provider calls permitted:** No  
**Batch 07 authorization included:** No

---

## Problem

Batch 06 produced a verified HTTP 400 request rejection at Condition C turn 3.

The protected diagnostic correctly classified the failure family as `request_rejected`, but the public error code was `PROVIDER_RESPONSE_INVALID`. That code describes a different boundary: a response that exists but cannot be validated.

The Batch 06 diagnostic also lacked enough content-free request-shape metadata to distinguish request construction, request size, parameter profile, and provider-state hypotheses during future failures.

---

## Resolution

This slice:

1. adds `PROVIDER_REQUEST_REJECTED` to the provider-neutral error taxonomy;
2. maps Groq 400-class request rejection to that distinct code;
3. preserves `PROVIDER_RESPONSE_INVALID` for actual response-envelope validation failures;
4. evolves the protected diagnostic contract from schema 1.2.0 to 1.3.0;
5. keeps schema 1.2.0 Batch 06 diagnostics readable with their historic mapping;
6. records content-free request shape for future request rejections;
7. classifies request-rejection reason into an allowlisted enum without retaining provider messages;
8. supports both nested and top-level provider error-body metadata shapes;
9. keeps request rejection non-retryable;
10. adds focused privacy, taxonomy, compatibility, and invariant tests.

---

## New request-rejection metadata

Schema 1.3.0 retains:

- adapter version;
- allowlisted rejection reason;
- message count;
- system-prompt byte count;
- user-prompt byte count;
- total prompt byte count;
- preflight input-token estimate;
- output-token budget;
- temperature in milli-units;
- streaming flag;
- storage flag;
- allowlisted reasoning effort;
- existing provider request-ID hash and allowlisted provider error fields.

It does not retain:

- prompt text;
- request messages;
- raw provider error body;
- provider error message;
- exception message;
- credentials;
- headers;
- raw response;
- provider output.

---

## Allowlisted rejection reasons

- `context_length`
- `invalid_parameter`
- `unsupported_parameter`
- `json_validation`
- `tool_use`
- `unknown`

Classification uses allowlisted provider codes first, then bounded in-memory message markers. Raw messages are discarded.

---

## Backward compatibility

Historic schema 1.2.0 request-rejection diagnostics remain valid with:

- family: `request_rejected`
- mapped code: `PROVIDER_RESPONSE_INVALID`
- no schema 1.3.0 request-shape fields

New schema 1.3.0 request rejection requires:

- mapped code: `PROVIDER_REQUEST_REJECTED`
- complete request-shape metadata
- non-retryable behavior
- internally consistent prompt byte counts

Batch 06 public evidence is not rewritten.

---

## Acceptance criteria

- focused contract and Groq diagnostic tests pass;
- full test suite passes;
- Ruff lint and formatting pass;
- mypy passes;
- Batch 06 `verify` still passes;
- the protected Batch 06 schema 1.2.0 diagnostic validates under the new contract;
- Batch 06 receipt remains rejected;
- no Batch 07 assets exist;
- no provider credential is required;
- no provider call occurs.

---

## Non-claims

This slice does not identify the Batch 06 root cause.

It does not prove:

- a Groq cache defect;
- cache-affinity causation;
- transient-provider causation;
- a successful retry policy;
- an accepted A/B/C result.

It improves the harness so that a separately authorized future diagnostic experiment can produce more discriminating evidence.
