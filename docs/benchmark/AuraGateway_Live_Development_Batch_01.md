# AuraGateway Live Development Batch 01

## Purpose

This slice introduces the first real-provider orchestration boundary after the controlled scripted smoke.
It authorizes exactly one frozen development episode, replication 01, and the A/B/C run triplet.
It does not authorize held-out execution, the full functional benchmark, the runtime microbenchmark,
or any comparative performance claim.

## Authorized scope

```text
episode=ep-func-001
replication=replication-01
conditions=condition_a,condition_b,condition_c
runs=3
turns_per_run=4
maximum_attempts=15
maximum_estimated_cost=5000 micro-USD
provider=Groq
model=openai/gpt-oss-20b
```

## Runtime prompt profile

The pilot uses `development-live-compact-v1`.

It derives a deterministic compact system prompt from the frozen compiler specification and uses the
frozen required sources for the selected development episode. This is a provider-orchestration pilot,
not a comparison-eligible benchmark run. Retrieval execution is intentionally replaced by verified
required-source injection so provider, retry, budget, protected-output, journal, and resume behavior can
be tested without tuning retrieval or inspecting held-out assets.

Condition behavior:

- Condition A mixes volatile turn state into the system message, producing a cache-hostile prefix.
- Condition B keeps the compact system message stable and places turn state in the user message.
- Condition C preserves the same stable prompt boundary and records session-start then warm-affinity
  route reasons while keeping the frozen Groq route.

## Evidence controls

Public evidence contains only:

- opaque run, trace, attempt, pair, and namespace IDs;
- hashes and versions;
- provider/model identities;
- bounded statuses and failure codes;
- token and duration telemetry where returned;
- estimated cost integers;
- structured-output and citation-scope validation states.

Raw provider output is written only to:

```text
.local/benchmark/live-development-v1/protected_outputs.jsonl
```

The public append-only journal is forced to disk after every attempt and terminal event. Resume preserves
completed terminal records. A run with attempts but no terminal record is safety-aborted rather than
blindly replayed because the prior provider response state may be uncertain.

## Commands

```powershell
auragateway-benchmark-live-development validate --authorization-id live-development-batch-01-auth-v1
auragateway-benchmark-live-development run --authorization-id live-development-batch-01-auth-v1
auragateway-benchmark-live-development resume --authorization-id live-development-batch-01-auth-v1
auragateway-benchmark-live-development verify --authorization-id live-development-batch-01-auth-v1
```

`run` requires `GROQ_API_KEY`, `AURAGATEWAY_PREFIX_HMAC_KEY`, and
`AURAGATEWAY_PREFIX_HMAC_KEY_ID` in the current process environment.

## Claim boundary

This slice may prove bounded real-provider invocation, metadata-safe attempt accounting, protected output
retention, retry regulation, ambiguous-response blocking, cost and attempt ceilings, and append-preserving
resume behavior on one development A/B/C triplet.

It does not prove provider cache reuse, latency reduction, cost reduction, task-quality non-inferiority,
feedback-quality improvement, held-out performance, full benchmark completion, deployment safety, or
production readiness.
