# ADR: Implement measured A/B/C execution authorization V1

Date: 2026-08-08

## Status

Implementation candidate.

## Context

The design boundary is merged on main `abb4fe30ebddb83bb9596bd2a4bcb6d114089d39`. The governed P5/P6 successor pass is
accepted, the 342-trajectory benchmark is eligible, and measured execution remains unauthorized.

The current repository also retains historical authorization and freeze artifacts for a
72-trajectory experiment and hosted-provider/Groq execution. They remain evidence only and
must never become current execution authority.

The variance pilot, repetition-count freeze, and current-line execution-manifest freeze do not
yet exist as a single terminal readiness authority.

## Decision

Implement the single-use authorization lifecycle now, but make issuance depend on one future
committed readiness record:

`benchmarks/local_abc/auragateway_measured_abc_execution_readiness_v1.json`

The issuer validates that record and every artifact receipt it binds. The issuer cannot create
or mutate readiness evidence.

This is a deliberate interface seam: variance-pilot and freeze work can evolve without
requiring the authorization lifecycle to be rewritten.

## Lifecycle

The module exposes:

- `generate`
- `validate-implementation`
- `issue`
- `verify`
- `consume`
- `abandon`

`issue` fails closed until the readiness record is committed and valid.

The issued capability is transient, non-overwriting, expiring, single-use, and bound to:

- synchronized main;
- the exact readiness record;
- the final execution manifest;
- preflight ledger and condition fingerprints;
- the current local-vLLM runtime;
- a fresh Kaggle capability observation;
- the exact operator-confirmation bytes;
- the exact execution budget.

After issuance, verification/terminalization requires the working tree to contain exactly one
untracked authorization artifact and no other drift.

## Budget

- trajectories: 342
- turns: 1,368
- maximum request attempts: 2,736
- maximum retries after initial attempt: 1
- hidden retries: 0
- replacement cases: prohibited
- Kaggle sessions: 1
- saved versions: 1
- external network requests: 0
- external spend: 0
- customer data: prohibited
- credentials: prohibited

## Historical lineage

The implementation hash-locks but does not reuse:

- `benchmarks/local_abc/measured_execution_authorization_v1.json`
- `data/evals/benchmark/freeze-v1/execution_manifest.json`
- `src/auragateway/local_abc/measured_authorization.py`

A change in those identities fails closed so historical lineage cannot silently be rewritten.

## Readiness interface

The future readiness record must prove:

- current P5 accepted;
- current P6 accepted;
- variance pilot accepted;
- repetition count frozen;
- current execution manifest frozen;
- frozen manifest retains `execution_enabled=false`;
- 342 trajectories / 1,368 turns / 2,736 maximum attempts;
- zero hidden retries;
- exact current ledger and condition-fingerprint identities;
- exact current execution-manifest receipt;
- exact current variance-pilot acceptance receipt;
- exact current repetition-count-freeze receipt;
- exact current governed P5/P6 acceptance receipt;
- current local-vLLM runtime binding;
- measured execution remains unauthorized before issuance.

## Consequences

The implementation PR itself cannot execute the benchmark. After merge, the next legal action
is to resolve the readiness record through variance/repetition/final-freeze work. Only then may
a fresh platform observation and explicit operator confirmation issue one capability.

## Non-claims

This ADR does not claim measured results, production readiness, customer-data readiness, or
authorization to execute A/B/C.
