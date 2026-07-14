# AuraGateway Groq Cache-Telemetry Reauthorization Review

## Result

```text
review_id: groq-cache-telemetry-reauthorization-review-v1
status: review_ready_inactive
decision: reauthorization_review_ready_inactive
source_commit: e639fca938e7d0309a185eff5c7fac533015d9ec
```

## Why reauthorization is review-ready

The first three-call calibration observed successful Groq responses but no billing cache
field in the parsed SDK objects. The subsequent compatibility review established that Groq
SDK `1.5.0` and the AuraGateway adapter correctly support the documented field and preserve
its presence state.

A duplicate parsed-only run is not justified. A future run becomes informative only by
capturing the raw response body and the parsed `ChatCompletion` from the same HTTP response.
That boundary can distinguish provider wire omission from live SDK parsing behaviour.

## Frozen lineage

The review binds eleven historical artifacts:

- the original prompt recipe;
- authorization and runtime policy;
- journal and typed run records;
- execution report and manifest;
- closeout and closeout manifest;
- SDK compatibility review and manifest.

The previous authorization remains consumed. Rerun and resume remain prohibited.

## Provider boundary checked

Official Groq prompt-caching documentation was checked on 2026-07-14.

```text
provider: Groq
model: openai/gpt-oss-20b
caching: automatic
exact prefix required: yes
cache hit guaranteed: no
expiry without use: 2 hours
minimum cacheable range: 128 to 1024 tokens, model-dependent
billing field: usage.prompt_tokens_details.cached_tokens
cached-input discount: 50%
```

The existing frozen prompt produced 1,401 observed input tokens per prior call, exceeding the
documented upper bound of the model-dependent minimum range.

## Materially different observation path

```text
old:
provider response -> SDK parse -> AuraGateway adapter -> public field-presence evidence

proposed:
provider response
  -> protected raw response bytes
  -> SDK parse from the same response
  -> protected parsed object
  -> AuraGateway public field-presence and parity evidence
```

Unchanged controls:

```text
provider
model
prompt recipe
protected prompt bundle
request hash
request parameters
adapter version
telemetry capture version
timeout
maximum completion tokens
temperature
streaming and storage settings
```

Changed control:

```text
observation boundary only
```

## Planned future execution

```text
attempt count: 2
maximum provider calls: 2
attempt 0: cold wire probe at 0 seconds
attempt 1: warm wire probe at 10 seconds
identical provider request required: yes
planned bounded cost: 400 micro-USD
authorization ceiling: 700 micro-USD
retry: false
resume: false
```

Two calls are enough to inspect cold and warm wire field presence. This review does not use
additional calls to manufacture confidence.

## Predeclared outcomes

### `wire_field_present_and_parsed`

The raw response contains a numeric billing field and the parsed SDK object preserves the
same value. Calibration-only provider cache usage evidence may be reported.

### `wire_field_present_but_parsed_absent`

The raw response contains a numeric field but the parsed object omits it. A live SDK parsing
defect is supported.

### `wire_field_absent`

The raw body itself omits the field. Provider wire omission is established for the observed
calls, but provider cache usage remains unavailable.

### `reauthorization_execution_failed`

A provider, evidence, privacy, integrity, or budget failure blocks all telemetry conclusions.

## Current authorization state

```text
provider calls performed: 0
credential accessed: false
provider call authorized: false
active authorization created: false
execution command available: false
reauthorization execution authorized: false
benchmark execution authorized: false
benchmark claims permitted: false
comparison eligible: false
```

## Privacy boundary

Raw and parsed provider content must remain protected and ignored:

```text
.local/benchmark/groq-cache-telemetry-reauthorization-v1/raw_responses.jsonl
.local/benchmark/groq-cache-telemetry-reauthorization-v1/parsed_responses.jsonl
```

Public evidence must contain metadata and hashes only. It must not contain prompts, response
bodies, output text, credentials, headers, or unrestricted provider payloads.

## Decision

Reauthorization is justified at the **review** level because the proposed raw-plus-parsed
boundary can answer a question the first calibration could not answer.

Execution remains inactive. The next slice is a separate activation that creates a new
one-time, two-call authorization without executing it.

## Non-claims

This review does not establish:

- a provider cache hit or miss;
- numeric cached tokens;
- the exact provider-internal omission cause;
- SDK failure on a live raw response;
- latency or cost improvement;
- comparison eligibility;
- A/B/C superiority;
- production readiness.
