# AuraGateway Live Development Batch 02

## Purpose

Batch 02 is a corrective development-only replay of the exact Batch 01 episode and A/B/C
triplet. Batch 01 remains immutable evidence.

The corrective boundary addresses two observed harness failures:

1. the provider followed the frozen compiler output schema while the live runner validated the
   separate canonical episode-runtime schema;
2. unpaced consecutive calls exhausted the hosted provider rate limit before the triplet could
   complete.

Batch 02 does not authorize held-out execution, the complete benchmark, measured comparison, or
performance claims.

## Root-cause evidence

The four successful Batch 01 calls returned valid single-object JSON matching the frozen compiler
fields:

- `decision`
- `answer`
- `citations`
- `missing_information`
- `escalation_reason`
- `confidence_band`

The runner instead expected canonical fields such as `reason_code`, `response`, and `citation_ids`.
The outputs were therefore rejected at the internal contract boundary despite following the
provider-facing schema.

## Corrective architecture

`ContractAlignedPacedAdapter` is a provider-boundary translator and cadence regulator.

For each successful provider call it:

1. retains the unmodified provider output under ignored local storage;
2. accepts either the canonical terminal contract or the frozen compiler contract;
3. deterministically normalizes supported compiler decisions into the canonical terminal contract;
4. returns the canonical protected output to the existing execution harness;
5. preserves telemetry while replacing only the protected output and its digest.

Compiler-schema refusal output is rejected because the frozen provider-facing schema lacks the
canonical refusal reason and safe alternative. The adapter does not invent those safety fields.

## Pacing policy

```text
policy=live-development-batch-02-runtime-policy-v1
minimum_call_interval_seconds=20
rate_limit_cooldown_seconds=65
maximum_cumulative_sleep_seconds=900
```

The pacing policy does not increase the authorized provider-call or retry budget. It spaces calls
and delays the next eligible call after an observed rate-limit response.

## Evidence locations

Public Batch 02 authorization and runtime policy:

```text
data/evals/benchmark/live-development-v2/authorization.json
data/evals/benchmark/live-development-v2/runtime_policy.json
```

Generated public Batch 02 evidence is written beneath:

```text
data/evals/benchmark/live-development-v2/
```

Canonical protected outputs consumed by the harness:

```text
.local/benchmark/live-development-v2/protected_outputs.jsonl
```

Unmodified provider outputs retained by the normalization boundary:

```text
.local/benchmark/live-development-v2/provider_raw_outputs.jsonl
```

Both local files remain ignored and must never be staged.

## Authorization

```text
authorization_id=live-development-batch-02-auth-v1
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

## Commands

```powershell
python -m auragateway.benchmark.execution_runner validate `
  --authorization-id live-development-batch-02-auth-v1

python -m auragateway.benchmark.execution_runner run `
  --authorization-id live-development-batch-02-auth-v1

python -m auragateway.benchmark.execution_runner resume `
  --authorization-id live-development-batch-02-auth-v1

python -m auragateway.benchmark.execution_runner verify `
  --authorization-id live-development-batch-02-auth-v1
```

## Acceptance criteria

- all three authorized runs retain terminal records;
- no successful compiler-schema output is mislabeled as structurally invalid;
- raw and canonical protected outputs remain ignored and locally retained;
- retry, attempt, input, cost, and cumulative pacing limits remain enforced;
- Batch 01 files remain byte-for-byte unchanged;
- held-out and full-benchmark execution remain prohibited.

A completed Batch 02 may establish that the corrective provider boundary works on this one
development triplet. It does not establish cache reuse, latency or cost improvement, quality
non-inferiority, full benchmark performance, deployment safety, or production readiness.
