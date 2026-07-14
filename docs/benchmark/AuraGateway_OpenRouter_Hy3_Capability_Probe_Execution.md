# AuraGateway OpenRouter Hy3 Capability-Probe Execution

## Current state

```text
implementation_status=execution runner implemented
live_provider_call_performed=false
authorization_status=active and unconsumed before live execution
historical_hash_bound_files_modified=false
next_gate=merge execution runner, return to clean main, execute once
```

## Execution contract

The one-time runner preserves the authorized two-call sequence:

```text
cold_probe
warm_probe
```

Both calls use the same protected stable prefix and the same protected OpenRouter session identity.
The exact outputs are:

```text
COLD-PROBE-ACK
WARM-PROBE-ACK
```

Only surrounding whitespace is ignored.

## Evidence ordering

For each attempt:

```text
attempt_started journal event
HTTP completion response retained
HTTP generation response retained, when requested
adapter parsing and reconciliation
parsed observation retained
observation_retained journal event
```

Each returned HTTP response receives its own protected raw JSONL record. This distinguishes completion
success from later generation-metadata failure.

## Retry rule

One replacement is permitted only when all conditions hold:

```text
completion request returned 429, 502, 524, or 529
no successful completion was received
this is the first attempt for the logical call
the four-attempt global ceiling remains open
```

A successful completion is never retried, including when output validation, generation metadata, route
identity, or telemetry validation later fails.

## Execution-specific promotion rule

Numeric measurement-channel evidence exists when at least one retained observation contains a numeric:

```text
cached_tokens
cache_write_tokens
native_tokens_cached
```

Controlled positive cache-use evidence requires:

```text
cold cache_write_tokens > 0
or
warm cached_tokens > 0
```

A positive cold cached-token read is retained and labelled cold-state contamination. It does not alone
permit promotion.

Promotion also requires:

```text
two retained successful observations
same requested model
same resolved model
same upstream provider
same session identity hash
valid completion/generation reconciliation
```

Promotion means only:

```text
promoted_to_pilot_authorization_review
```

It does not authorize the pilot.

## Terminal outcomes

```text
closed_transient_budget_exhausted
closed_terminal_provider_failure
closed_observation_invalid
closed_route_unidentifiable
closed_telemetry_unavailable
closed_no_cache_use
closed_interrupted_execution
promoted_to_pilot_authorization_review
```

## Authorization consumption

The committed authorization JSON remains unchanged. The one-time runtime authorization is consumed by:

```text
.local/benchmark/openrouter-hy3-capability-probe-v1/terminal_receipt.json
```

The receipt binds the terminal outcome to attempt counts, source commit, prompt and preflight hashes,
and protected journal/raw/parsed evidence hashes.

## Inactive implementation claim

> AuraGateway contains a reviewed, fixture-tested, fail-closed one-time execution path for the authorized
> OpenRouter Hy3 capability probe. The implementation change itself performs no live provider call.

## Non-claims

```text
No Hy3 inference has been performed by this implementation slice.
No numeric Hy3 cache telemetry has been observed.
No cache read, cache write, hit, miss, cost saving, or latency saving has been established.
No A/B/C pilot or retained benchmark is authorized.
```
