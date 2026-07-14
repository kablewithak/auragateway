# ADR: Permit an Inactive Raw-Wire Reauthorization Review

**Status:** Accepted for review; inactive for execution  
**Date:** 2026-07-14  
**Review ID:** `groq-cache-telemetry-reauthorization-review-v1`  
**Source commit:** `e639fca938e7d0309a185eff5c7fac533015d9ec`

## Context

The first Groq cache-telemetry calibration executed three identical requests against
`openai/gpt-oss-20b`. All three calls succeeded, but every parsed SDK response omitted
`usage.prompt_tokens_details.cached_tokens`. The calibration closed as
`closed_billing_field_unavailable`.

The follow-up SDK compatibility review proved:

- Groq SDK `1.5.0` models `usage.prompt_tokens_details.cached_tokens`;
- real SDK objects preserve absent, null, zero, and positive presence states correctly;
- the existing AuraGateway adapter preserves those states;
- no SDK upgrade or adapter correction is justified;
- the exact live omission cause remains unresolved.

Repeating the same requests through the same parsed-object-only boundary would add little
information and would not meet AuraGateway's evidence-efficiency standard.

Current official Groq prompt-caching documentation, retrieved on 2026-07-14, states that:

- `openai/gpt-oss-20b` supports automatic prompt caching;
- cache hits require exact prefix matching and are not guaranteed;
- the cache expires after two hours without use;
- minimum cacheable length varies from 128 to 1024 tokens by model;
- billing cache evidence is reported at
  `usage.prompt_tokens_details.cached_tokens`;
- cached input receives a 50% discount when a cache hit occurs.

The installed Groq SDK exposes
`client.chat.completions.with_raw_response.create`, which can retain the raw HTTP response
and parse the `ChatCompletion` from the same response object.

## Decision

Approve a **review-ready but inactive** reauthorization design using a materially different
observation boundary:

```text
prior boundary:
parsed SDK ChatCompletion only

proposed boundary:
raw HTTP response body plus parsed SDK ChatCompletion from the same response
```

The provider, model, exact prompt, request parameters, adapter identity, and timing remain
unchanged. Only the observation boundary changes.

The proposed future execution contains two identical requests:

```text
attempt 0: cold wire probe at 0 seconds
attempt 1: warm wire probe at 10 seconds
```

Two calls are sufficient because the primary question is wire-versus-parser field presence,
not latency estimation. A third repeat would increase cost without materially expanding the
classification space.

## Information gain

A future activated run could distinguish:

1. **Wire field present and parsed**
   - the provider emitted numeric cache evidence;
   - the SDK preserved it;
   - provider cache usage may be described for this calibration only.

2. **Wire field present but parsed absent**
   - a live SDK parsing defect is supported despite synthetic compatibility;
   - the raw numeric value may support a calibration-only provider cache observation.

3. **Wire field absent**
   - provider wire omission is established for the observed calls;
   - SDK parsing is no longer a plausible explanation for those responses;
   - cache usage remains unavailable.

4. **Execution failed**
   - no wire-omission or cache-usage conclusion is permitted.

## Authorization boundary

This ADR does not activate execution.

```text
provider calls performed: 0
credential access: none
provider calls authorized: false
active authorization created: false
execution command available: false
retry permitted: false
resume permitted: false
benchmark execution authorized: false
comparison eligible: false
```

A separate activation slice must create a new one-time authorization lineage. The consumed
calibration authorization remains immutable and cannot be reopened or resumed.

## Privacy and evidence controls

Future raw and parsed responses must remain under separate ignored local paths:

```text
.local/benchmark/groq-cache-telemetry-reauthorization-v1/raw_responses.jsonl
.local/benchmark/groq-cache-telemetry-reauthorization-v1/parsed_responses.jsonl
```

Public evidence may retain only bounded metadata such as:

- response and request hashes;
- field-presence states;
- numeric token counts where observed;
- SDK version;
- timings;
- typed classifications;
- evidence-integrity hashes.

Public artifacts must not retain raw prompts, raw response bodies, model output text,
credentials, headers, or unrestricted provider metadata.

## Consequences

### Positive

- the new run has explicit incremental information value;
- wire omission and SDK parsing become separately testable;
- the model and request remain fixed, avoiding a model-change confound;
- the call count is reduced from three to two;
- historical evidence remains immutable;
- claims remain machine-blocked until activation, execution, and closeout.

### Negative

- raw HTTP bodies create a stronger protected-data handling obligation;
- even a wire-level omission will not reveal the provider-internal cause;
- a successful calibration still will not make the A/B/C benchmark comparison-ready;
- another activation and closeout lifecycle is required.

## Rejected alternatives

### Repeat the original parsed-only calibration

Rejected because it does not materially change the observation boundary.

### Change to `openai/gpt-oss-120b` immediately

Rejected for this slice because changing the model and observation boundary together would
confound the diagnosis. Model-specific follow-up may be considered only after wire-level
behaviour for the frozen `20b` request is known.

### Bypass the SDK with a separate handwritten HTTP client

Rejected because the SDK already provides a raw-response surface. Reusing the official
client preserves request construction and reduces duplicate integration logic.

### Restart A/B/C execution

Rejected because numeric billing cache telemetry and comparison eligibility remain
unresolved.

## Next gate

```text
groq_cache_telemetry_reauthorization_activation
```

That gate may create an active two-call authorization. It must not execute the calls in the
same unreviewed step.
