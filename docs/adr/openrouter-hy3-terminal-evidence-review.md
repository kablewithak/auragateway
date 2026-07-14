# ADR: Close the OpenRouter Hy3 Capability Lineage After Pre-Inference Authentication Failure

| Field | Value |
|---|---|
| Status | Accepted |
| Decision date | 2026-07-14 |
| Project | AuraGateway v2 |
| Review ID | `openrouter-hy3-terminal-evidence-review-v1` |
| Source closeout | `openrouter-hy3-capability-probe-closeout-v1` |

## Context

AuraGateway opened a separate OpenRouter `tencent/hy3:free` lineage after the closed Groq path failed
to expose the numeric cached-token field required for the measured A/B/C benchmark.

The OpenRouter extension completed:

- route and identifiability review;
- generic adapter and telemetry fixture validation;
- bounded authorization and state-model review;
- protected prompt preparation;
- metadata-only key and model-catalog preflight;
- execution-runner implementation and merge;
- one authorized live cold attempt;
- sanitized terminal closeout.

The live cold attempt returned HTTP `401` before a successful completion. The runner classified the
response as `PROVIDER_AUTHENTICATION_FAILED`, prohibited retry, did not request generation metadata,
did not issue the warm call, consumed the authorization, and produced a terminal receipt.

The public evidence cannot prove the exact credential/header root cause.

## Decision

Close the OpenRouter Hy3 capability lineage permanently with terminal outcome:

```text
closed_terminal_provider_failure
```

Do not resume or rerun the authorization.

Do not authorize:

```text
A/B/C pilot
retained benchmark
cache, affinity, latency, or cost claims
```

Treat the result as a pre-inference authentication failure rather than as:

```text
Hy3 model failure
route unavailability
privacy-routing failure
cache telemetry absence
cache hit or miss
```

Preserve the post hoc header-construction test only as local regression evidence. Do not use it to
claim what OpenRouter received during the consumed live attempt.

## Rationale

The authorization was explicitly one-time, non-resumable, and non-rerunnable. HTTP `401` was not in
the frozen transient replacement set. Repeating the call would violate the reviewed execution
constitution and would turn governance into outcome-seeking.

The experiment’s purpose was to determine whether the measurement channel could be trusted under a
fixed protocol. A terminal failure before successful inference is a valid result when the harness
retains it honestly and blocks unsupported promotion.

## Consequences

### Positive

- Preserves the integrity of the one-time authorization.
- Keeps the failed attempt and exact evidence stage visible.
- Prevents an authentication failure from being misreported as a cache result.
- Maintains independent Groq and OpenRouter lineages.
- Produces a useful harness-hardening case study.

### Negative

- Numeric Hy3 cache telemetry remains unknown.
- The A/B/C comparison remains incomplete.
- The exact authentication root cause remains unresolved.
- A future provider experiment requires a new lineage and authorization.

## Future-lineage requirements

Any new provider capability probe must add:

```text
protected credential fingerprint continuity
strict surrounding-whitespace rejection
non-sensitive exact-live-request header-construction evidence
new provider/model namespace
new authorization and protected evidence directory
explicit non-rerun relationship to closed lineages
```

## Claims

Permitted:

> The OpenRouter Hy3 capability probe closed on its first cold attempt after HTTP `401`; no successful
> completion, generation metadata, route identity, or cache telemetry was obtained.

Blocked:

```text
OpenRouter omitted the header
Hy3 was unavailable
cache telemetry was absent from a successful response
cache use or savings occurred
Condition C was evaluated
```
