# AuraGateway Gate 11 — Development Controlled Smoke

## Status

```text
Gate: 11
Scope: Development-only scripted A/B/C execution smoke
Live provider calls: No
Held-out episodes: Prohibited
Full benchmark execution: Prohibited
Benchmark claims: Prohibited
Measured execution permitted: No
```

## Purpose

Gate 10 froze the exact execution manifest but intentionally kept execution disabled. Gate 11
validates the runner state machine before any live functional benchmark begins.

The smoke consumes one already-frozen development episode and one frozen replication pair across
Conditions A, B, and C. It executes metadata-only scripted provider outcomes. This proves runner
regulation, terminal accountability, retry control, ambiguous-response blocking, budget kill
switches, and resume behavior without spending provider budget or inspecting held-out results.

## Authorization boundary

Execution-manifest freeze and execution authorization are separate controls.

The smoke requires the exact authorization ID:

```text
development-controlled-smoke-auth-v1
```

The authorization pins:

- the Gate 10 manifest bytes;
- the frozen execution-manifest canonical SHA-256;
- the Gate 9 manifest bytes;
- the 342-run planned-ledger bytes;
- the frozen functional episode-set bytes;
- one development episode;
- one replication-01 A/B/C pair;
- three exact run IDs;
- eleven total scripted attempts;
- a 5,000 micro-USD synthetic accounting ceiling;
- no live provider execution;
- no held-out execution;
- no full benchmark execution;
- no benchmark claims.

## Selected development pair

```text
Episode: ep-func-001
Split: development
Replication: replication-01
Conditions: A, B, C
Runs: 3
Turns per run: 4
```

The three cache namespaces remain distinct.

## Scripted failure coverage

Condition A completes four turns without retry.

Condition B receives one definite retryable provider failure on turn two. The runner permits one
retry only because response certainty is definite, the error is retryable, the retry remains on
the same turn, and the logical-request fingerprint is unchanged.

Condition C completes turn one and receives an ambiguous provider response on turn two. The runner
blocks retry and records `aborted_safety_control` with
`AMBIGUOUS_PROVIDER_RESPONSE`.

## Terminal accountability

Every authorized run receives exactly one terminal record. Attempt records are immutable,
metadata-only, and linked by opaque trace, attempt, and terminal identifiers.

Resume behavior is append-preserving:

- terminal records are never overwritten;
- existing attempts are never deleted;
- only runs without terminal evidence may execute;
- resuming a fully terminal smoke produces identical evidence bytes.

## Budget controls

Before each scripted attempt the runner checks:

- global attempt count;
- global synthetic cost accounting;
- per-turn retry ceiling;
- ambiguous-response safety state.

A blocked attempt becomes an explicit `budget_exhausted`, `provider_error`, or
`aborted_safety_control` terminal state. It never disappears from evidence.

## Privacy boundary

Retained smoke evidence contains only:

- IDs and hashes;
- condition and episode identities;
- bounded statuses and failure codes;
- token counts;
- latency integers;
- synthetic cost-accounting integers.

It contains no raw prompts, user messages, retrieved text, model output, provider payloads,
credentials, protected review content, or hidden reasoning.

## Commands

```text
auragateway-benchmark-controlled-smoke validate
auragateway-benchmark-controlled-smoke run
auragateway-benchmark-controlled-smoke resume
auragateway-benchmark-controlled-smoke verify
```

Every command requires the explicit authorization ID. No command calls Groq, Ollama, or another
live provider.

## Gate result

Gate 11 passes when:

- all upstream hashes reproduce;
- the selected episode is development-only;
- the exact A/B/C run pair is selected;
- all three terminal records exist;
- the definite failure receives exactly one safe retry;
- the ambiguous response receives no retry;
- attempt and cost budgets remain respected;
- resume preserves terminal evidence;
- no live provider call occurs;
- no held-out or full benchmark execution occurs.

## Claim boundary

This gate proves deterministic runner regulation on fixed scripted metadata.

It does not prove live provider execution, provider cache reuse, latency savings, cost savings,
measured task quality, measured feedback quality, full benchmark readiness, deployment safety, or
production readiness.
