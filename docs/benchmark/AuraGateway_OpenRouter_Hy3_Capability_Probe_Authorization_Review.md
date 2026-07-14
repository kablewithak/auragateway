# AuraGateway OpenRouter Hy3 Capability-Probe Authorization Review

## Result

```text
status: review_ready_inactive
source commit: 723419ad042e7017613467c5a69765f90267e5c9
requested model: tencent/hy3:free
credential accessed: false
network request performed: false
provider call authorized: false
next gate: openrouter_hy3_capability_probe_activation
```

## What this slice establishes

The slice adds an explicit-key, zero-automatic-retry OpenRouter HTTP transport and freezes the
runtime constitution for a future two-call capability probe.

The transport owns only HTTP serialization, authentication headers, bounded response parsing, and
safe status mapping. It does not read environment variables, choose retry timing, consume an
authorization, write evidence, or promote the experiment.

## Current provider facts

As reviewed on July 14, 2026:

```text
route: tencent/hy3:free
price: free
release date: 2026-07-06
scheduled retirement: 2026-07-21
context window: 262144
```

OpenRouter documents that the same model may be hosted by different companies. The exact eligible
endpoint count and availability under `data_collection=deny` plus `zdr=true` remain unverified.

## Key and limit preflight

The activation must call `GET /api/v1/key` before inference and retain metadata-safe values for:

```text
is_free_tier
limit
limit_remaining
usage_daily
```

The endpoint does not expose exact remaining free-model requests. Successful inference responses do
not include rate-limit headers. AuraGateway therefore relies on its own absolute ceiling rather than
claiming to know the remaining OpenRouter request quota.

## Runtime constitution

```text
logical calls: 2
roles: cold_probe, warm_probe
maximum provider successes: 2
maximum retained successes: 2
maximum inference attempts: 4
maximum transient replacements per logical call: 1
transient statuses: 429, 502, 524, 529
resume permitted: false
rerun permitted: false
```

A successful response is never repeated. Failure to obtain or reconcile generation metadata after a
successful inference closes the run as observation-invalid.

## Stable synthetic prompt

The public recipe deterministically produces:

```text
stable prefix bytes: 53080
stable prefix SHA-256: 1efb8ad1cd1763ad72645142636a18fc46fd330dd69fcf0ce02c5f84c0370420
estimated input-token band: 12000..16000
output token budget: 32
```

The prompt contains synthetic inert blocks only. The activation will place generated prompt content
under `.local`; public evidence receives hashes and byte counts only.

## Executable state-model result

```text
reachable states: 88
terminal states: 57
maximum attempts observed: 4
maximum provider successes observed: 2
maximum retained successes observed: 2
invariant violations: 0
```

The model includes terminal outcomes for telemetry unavailable, numeric telemetry without cache use,
route identity failure, observation failure, provider failure, transient-budget exhaustion, and
promotion to a later pilot authorization review.

## TLA+ decision

TLA+ is not added as a release dependency. The finite state space is exhaustively explored by an
executable Python model that runs under the existing pytest, Ruff, and mypy toolchain.

Non-claim:

```text
TLA+ model checking performed: false
```

## Claims

Permitted:

- the explicit-key HTTP transport is deterministic and has no automatic retry;
- the attempt, replacement, closeout, and promotion policies are frozen;
- the finite state space has been exhaustively checked by the executable model;
- the deterministic synthetic prompt recipe reconciles to its frozen hash and byte count;
- the package is ready for a separate activation review.

Blocked:

- a privacy-compatible Hy3 free endpoint is reachable;
- the account has sufficient free quota;
- Hy3 free returns numeric cache telemetry;
- Hy3 free uses prompt caching;
- Condition C improves cache retention;
- the A/B/C pilot is authorized;
- TLA+ verification occurred.

## Next gate

```text
openrouter_hy3_capability_probe_activation
```

That activation must bind the API-key preflight, protected prompt bundle, write-through journal,
one-time confirmation phrase, and executable closeout path before making any provider call.
