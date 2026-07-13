# AuraGateway Assistant-Content-Missing Response-Shape Diagnostics

## Status

```text
slice=phase-7-assistant-content-missing-response-shape-diagnostics
batch_04=preserved_failed_evidence
batch_05_authorization=blocked
live_provider_execution=not_permitted_by_this_slice
```

## Problem

Batch 04 classified one Condition C failure as `assistant_content_missing`, but the retained diagnostic
could not distinguish whether the provider response ended because of a normal stop, token exhaustion,
tool-call generation, reasoning-only output, refusal metadata, or a provider anomaly.

The missing evidence was response shape, not response content.

## Contract extension

Provider failure diagnostics now use schema version `1.1.0` and may retain the following fields only for
`assistant_content_missing` failures:

```text
response_id_sha256
response_choice_count
response_finish_reason_allowlisted
assistant_content_state
response_usage_present
response_completion_tokens
reasoning_present
reasoning_byte_count
tool_call_count
refusal_present
refusal_byte_count
```

`assistant_content_state` distinguishes:

```text
null
empty
whitespace
```

Allowlisted finish reasons are:

```text
stop
length
tool_calls
function_call
```

Unknown finish reasons are discarded rather than persisted.

## Privacy boundary

The adapter must never retain:

```text
reasoning text
refusal text
tool-call IDs
function names
function arguments
response IDs in plaintext
raw provider responses
raw prompts
raw documents
credentials
secrets
```

Reasoning and refusal are represented only as booleans and UTF-8 byte counts. Tool calls are represented
only as a count. Provider response IDs are SHA-256 hashed before persistence.

## Runtime behavior

For a typed Groq response with no usable visible assistant content, the adapter:

1. classifies content as null, empty, or whitespace;
2. records the number of choices;
3. retains an allowlisted finish reason when available;
4. records whether usage metadata exists and the reported completion-token count when available;
5. records reasoning, refusal, and tool-call presence without retaining their content;
6. hashes the provider response ID;
7. appends one protected diagnostic record;
8. raises the existing non-retryable `PROVIDER_RESPONSE_AMBIGUOUS` error.

The public provider-neutral error mapping does not change.

## Evaluation gate

The fixed tests prove:

- null, empty, and whitespace content are distinct;
- response IDs are hashed;
- allowlisted finish reasons are retained;
- unknown finish reasons are dropped;
- usage absence remains unknown rather than becoming zero;
- reasoning text is never retained;
- refusal text is never retained;
- tool-call payloads and arguments are never retained;
- response-shape metadata is rejected for unrelated failure families;
- incomplete response-shape diagnostics fail typed validation;
- successful calls do not create failure diagnostics;
- existing request-rejection, rate-limit, SDK-schema, and privacy behavior remains intact.

## Next gate

After this slice merges, a separate Batch 05 authorization may be prepared. Batch 05 must use a fresh
public evidence root and protected diagnostic root. It must run exactly once and stop for receipt and
response-shape review before any evidence is committed.
