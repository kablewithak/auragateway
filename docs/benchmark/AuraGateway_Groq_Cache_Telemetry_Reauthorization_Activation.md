# AuraGateway Groq Cache Telemetry Reauthorization Activation

**Authorization ID:** `groq-cache-telemetry-reauthorization-auth-v1`

**Execution ID:** `groq-cache-telemetry-reauthorization-v1`

**Status:** `active`

**Provider calls performed in this slice:** 0

**Credential accessed in this slice:** No

**Execution command available:** Yes

**Benchmark execution authorized:** No

**Comparison eligible:** No

**Next gate:** `live_reauthorization_preflight`

## Purpose

This slice activates the reviewed two-call raw-wire calibration. It does not
execute the calibration.

## Frozen observation plan

| Attempt | Role | Planned offset |
|---:|---|---:|
| 0 | Cold wire probe | 0 seconds |
| 1 | Warm wire probe | 10 seconds |

Both attempts use the same prompt bundle and exact provider request identity.

## Frozen provider profile

```text
provider: Groq
model alias: groq-gpt-oss-20b
exact model: openai/gpt-oss-20b
adapter: groq-chat-completions-v1
telemetry capture: groq-cache-telemetry-capture-v1
raw capture: groq-raw-response-capture-v1
maximum completion tokens: 32
temperature: 0
streaming: false
storage: false
reasoning effort: low
timeout: 30 seconds
```

## Active controls

```text
maximum provider calls: 2
planned maximum estimated cost: 400 micro-USD
authorization cost ceiling: 700 micro-USD
retry: forbidden
resume: forbidden
rerun: forbidden
benchmark execution: forbidden
comparison eligibility: false
```

Execution requires:

```text
authorization ID:
groq-cache-telemetry-reauthorization-auth-v1

confirmation phrase:
EXECUTE_GROQ_CACHE_TELEMETRY_REAUTHORIZATION_ONCE
```

## Observation boundary

Each provider call must produce two protected views of the same response:

```text
exact raw HTTP response bytes
parsed Groq ChatCompletion object
```

The public record retains only hashes, byte counts, HTTP status, SDK version,
field-presence states, and numeric cached-token values where observed.

Protected files:

```text
.local/benchmark/groq-cache-telemetry-reauthorization-v1/raw_responses.jsonl
.local/benchmark/groq-cache-telemetry-reauthorization-v1/parsed_responses.jsonl
```

## One-time behavior

Any existing journal, run-record set, report, execution manifest, protected raw
response file, or protected parsed response file blocks execution.

A partial or failed run therefore consumes the practical execution opportunity.
Recovery requires a new reviewed authorization.

## Activation result

```text
active authorization created: true
provider calls performed: 0
credential accessed: false
execution completed: false
prior calibration reopened: false
benchmark execution authorized: false
```

## Next operational step

After this activation merges:

1. create a dedicated live evidence branch;
2. run non-live validation;
3. load `GROQ_API_KEY` without printing it;
4. run live preflight;
5. execute the exact two-call authorization once;
6. remove the credential immediately;
7. paste the live execution receipt before staging evidence;
8. inspect, verify, classify, and close out the result.

## Non-claims

This activation does not establish cache use, cache savings, latency
improvement, cost improvement, provider wire omission, SDK parsing failure,
comparison eligibility, A/B/C superiority, or production readiness.
