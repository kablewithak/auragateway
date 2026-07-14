# ADR: Activate One-Time Groq Raw-Wire Cache Telemetry Reauthorization

**Status:** Accepted

**Decision ID:** `groq-cache-telemetry-reauthorization-activation-v1`

## Context

The original three-call calibration closed as
`closed_billing_field_unavailable`. The later SDK compatibility review showed
that Groq SDK `1.5.0` models the documented billing field and that the existing
AuraGateway adapter preserves absent, null, zero, and positive field states.

The reauthorization review then qualified one materially different observation
boundary:

```text
raw HTTP response bytes
+
parsed Groq ChatCompletion
+
both derived from the same HTTP response
```

Repeating the parsed-only calibration would add little information. A two-call
raw-versus-parsed calibration can distinguish provider wire omission from a live
SDK parsing divergence while keeping the provider, model, prompts, request
parameters, and adapter identity fixed.

## Decision

Activate a new one-time authorization for exactly two provider calls:

| Attempt | Role | Offset |
|---:|---|---:|
| 0 | `cold_wire_probe` | 0 seconds |
| 1 | `warm_wire_probe` | 10 seconds |

The authorization:

- binds the exact PR #51 review assets;
- reuses the original protected prompt bundle byte-for-byte;
- freezes Groq model `openai/gpt-oss-20b`;
- freezes Groq SDK raw-response surface
  `client.chat.completions.with_raw_response.create`;
- requires the exact confirmation phrase
  `EXECUTE_GROQ_CACHE_TELEMETRY_REAUTHORIZATION_ONCE`;
- permits no retry, resume, rerun, or benchmark execution;
- caps calls at two;
- caps planned estimated cost at 400 micro-USD;
- caps authorization estimated cost at 700 micro-USD;
- retains raw and parsed responses only beneath ignored `.local` storage;
- records public metadata, hashes, field-presence states, and numeric token
  values only;
- blocks execution when any terminal public or protected evidence already
  exists.

## Runtime commands

The activation exposes:

```text
validate
live-preflight
run
verify
```

Only `run` may call Groq. It requires both the active authorization ID and exact
confirmation phrase.

The activation slice itself performs no provider call and does not read a
credential.

## Predeclared outcomes

### `wire_field_present_and_parsed`

The wire response contains a numeric
`usage.prompt_tokens_details.cached_tokens` value and the parsed SDK object
preserves the same value.

### `wire_field_present_but_parsed_absent`

The wire response contains a numeric billing field but the parsed SDK object
does not preserve it.

### `wire_field_absent`

Both successful raw responses omit the billing field. This permits only the
bounded claim that the observed provider wire responses omitted the field.

### `reauthorization_execution_failed`

A provider, observation, privacy, integrity, or evidence-write failure prevents
a telemetry conclusion.

## Evidence boundary

Public evidence may include:

- attempt identity;
- request hash;
- timing;
- HTTP status;
- raw and parsed byte hashes;
- field-presence states;
- numeric cached-token values when observed;
- SDK version;
- typed outcome and claim decisions.

Protected local evidence may include:

- exact raw response bytes encoded in JSONL;
- parsed SDK response objects;
- model output text contained in those responses.

Public evidence must never include raw prompts, raw response bodies, model
output text, credentials, headers, or unrestricted provider metadata.

## Consequences

Positive:

- the new run can distinguish provider wire omission from live SDK parsing;
- the intervention remains single-variable;
- two calls are sufficient for the diagnostic question;
- historical calibration evidence remains immutable;
- rerun and outcome-shopping remain blocked.

Trade-offs:

- raw provider responses require stronger local retention discipline;
- interrupted execution cannot resume;
- a terminal execution still requires a separate closeout;
- the result remains comparison-ineligible and cannot establish savings.

## Non-claims

Activation does not establish:

- a cache hit or cache miss;
- numeric cached tokens;
- provider wire omission on a new response;
- a live SDK parsing defect;
- latency or cost improvement;
- A/B/C superiority;
- production readiness.
