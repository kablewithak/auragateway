# AuraGateway Cache Telemetry Calibration Authorization Review

**Review ID:** `groq-cache-telemetry-calibration-review-v1`

**Status:** `review_ready_inactive`

**Provider calls authorized:** No

**Execution command available:** No

**Next gate:** `cache_telemetry_calibration_activation`

## Decision

The three-call cache telemetry calibration is technically review-ready, but it
remains inactive.

This slice freezes what would execute and how evidence would be classified. It
does not perform or authorize the provider calls.

## Source boundary

The review binds the PR #45 merge state and the exact Git blobs for:

- cache telemetry hardening acceptance;
- inactive calibration draft;
- hardening manifest;
- deterministic synthetic cases;
- cache telemetry capture contracts;
- provider call envelope;
- Groq adapter;
- hardening validator.

Any bound source drift invalidates the review.

## Provider documentation boundary

The official Groq prompt-caching documentation states that:

- caching is automatic on supported requests;
- `openai/gpt-oss-20b` is supported;
- cache hits require exact prompt-prefix matching;
- model-specific cacheable minimums range from 128 to 1,024 tokens;
- cache hits are not guaranteed;
- cached data expires after two hours without use;
- billing cache usage is reported through
  `usage.prompt_tokens_details.cached_tokens`;
- cached input portions receive a 50% discount.

Documentation establishes provider capability, not a cache hit for these
requests.

## Frozen request profile

- provider: Groq
- model alias: `groq-gpt-oss-20b`
- exact model: `openai/gpt-oss-20b`
- adapter: `groq-chat-completions-v1`
- telemetry capture: `groq-cache-telemetry-capture-v1`
- max completion tokens: 32
- temperature: 0
- streaming: false
- storage: false
- reasoning effort: low
- timeout: 30 seconds

## Protected prompt identity

Public evidence retains only:

- prompt byte counts;
- conservative token estimate;
- system and user SHA-256 values;
- provider request SHA-256;
- protected prompt-bundle SHA-256.

Raw synthetic prompt text is materialized only beneath ignored `.local`
storage.

The request contains 8,448 prompt bytes and a conservative estimate of 2,112
input tokens. This exceeds the documented upper end of the provider's
model-dependent cacheable minimum range by 1,088 tokens.

## Dry-run schedule

| Attempt | Role | Offset | Provider request |
|---|---|---:|---|
| 0 | cold | 0 seconds | exact frozen hash |
| 1 | warm repeat one | 10 seconds | identical |
| 2 | warm repeat two | 20 seconds | identical |

Dry-run result:

- planned attempts: 3
- unique provider requests: 1
- repeated provider requests: 2
- minimum planned elapsed time: 20 seconds
- estimated maximum cost: 600 micro-USD
- authorization ceiling: 1,000 micro-USD
- provider calls performed: 0

## Stop policy

The future calibration must stop on:

- any provider error;
- request hash mismatch;
- missing successful-response telemetry shape;
- public evidence write failure;
- protected-output write failure;
- budget exhaustion;
- privacy-boundary violation.

Retries and resume are forbidden.

## Future outcome classification

### Telemetry observed with cache hit

Requires three successful calls, numeric billing cache values on all three
calls, and a positive cached-token value on at least one warm repeat.

This can support a provider-cache observation for this calibration only.

### Telemetry observed without cache hit

Requires three successful calls, numeric billing cache values on all three
calls, and zero cached tokens on both warm repeats.

This establishes measured cache misses for this calibration. It does not prove
that prompt caching is unavailable generally.

### Billing cache field unavailable

Applies when at least one successful call exposes an absent or null billing
cache field.

Cache-usage and savings claims remain blocked.

### Calibration execution failed

Applies to provider, integrity, retention, privacy, or budget failures.

No retry or resume is permitted.

## Evidence destinations

Future public evidence:

- `journal.jsonl`
- `run_records.json`
- `report.json`
- `manifest.json`

Future protected local evidence:

- synthetic prompt bundle;
- raw provider outputs.

No raw prompt, output, credential, header, or provider payload may enter public
evidence.

## Claim boundary

This review does not establish:

- a provider cache hit;
- provider cache savings;
- latency improvement;
- cost improvement;
- B or C superiority;
- accepted A/B/C comparison;
- production readiness.

## Commercial translation

This is a strong AI System Evaluation Audit proof asset: the project validates
whether required provider evidence exists before spending a larger benchmark
budget or making a favorable cache claim.
