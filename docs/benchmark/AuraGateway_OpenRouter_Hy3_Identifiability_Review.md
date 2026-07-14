# AuraGateway OpenRouter Hy3 Identifiability Review

## Result

```text
status: review_ready_inactive
gateway provider: openrouter
requested model: tencent/hy3:free
adapter implementation: permitted
dry-run harness: permitted
live provider call: not authorized
pilot: not authorized
retained benchmark: not authorized
next gate: openrouter_provider_adapter_dry_run
```

## Current route facts

As of July 14, 2026, OpenRouter lists `tencent/hy3:free` as a free 262K-context route released on
July 6, 2026 and scheduled to go away on July 21, 2026.

This review does not prove how many privacy-compatible endpoints are currently eligible.

## Telemetry authority

OpenRouter documents normalized cache fields at:

```text
usage.prompt_tokens_details.cached_tokens
usage.prompt_tokens_details.cache_write_tokens
```

It also exposes generation metadata including model, provider name, session ID, cache discount, and
native cached-token count.

These are OpenRouter observations. They are not Tencent-direct infrastructure telemetry.

## Experimental controls

```text
Condition A:
unstable prefix
unique session ID per request

Condition B:
deterministic stable prefix
unique session ID per request

Condition C:
deterministic stable prefix
stable AuraGateway-derived session ID
```

OpenRouter documents that explicit `session_id` replaces its message-derived routing key. This makes
A versus B a context-construction comparison and B versus C an explicit affinity comparison.

Manual provider ordering is prohibited for B versus C because OpenRouter documents that it disables
sticky routing.

## Privacy boundary

Any future live request must use:

```text
synthetic public-safe prompt
provider.data_collection = deny
provider.zdr = true
no customer data
no private repository text
no historical .local prompt bundle
no public raw provider body
```

Privacy-compatible route availability remains a live preflight question.

## Future call constitution

```text
maximum successful calls: 2
maximum total attempts: 4
replacement statuses: 429, 502, 524, 529
replacement only before usable evidence
no retry after any successful usable response
```

The review itself performs zero calls and reads no credential.

## Claims

Permitted:

- the free route was visible and time-limited on the review date;
- OpenRouter documents normalized cache fields;
- OpenRouter documents explicit session stickiness;
- OpenRouter documents generation route metadata;
- the A/B and B/C interventions are frozen and distinguishable by design.

Blocked:

- Hy3 free returns numeric cache telemetry;
- Hy3 free used prompt caching;
- Condition C improves cache retention;
- multiple eligible endpoints exist;
- a privacy-compatible endpoint is currently reachable;
- the benchmark is eligible.

## Next gate

Implement a generic OpenRouter adapter and deterministic dry-run harness. Reassess the execution
state machine and TLA+ value before creating any live authorization.
