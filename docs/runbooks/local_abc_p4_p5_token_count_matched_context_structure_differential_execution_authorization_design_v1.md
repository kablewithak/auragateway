# Runbook — P4/P5 Token-Count-Matched Context-Structure Differential Execution Authorization Design V1

## Purpose

Operate the static authorization-design tranche only. This runbook does not grant live authority and does not permit Kaggle, GPU, worker, model-load, or model-request execution.

## Required Starting State

- branch starts from clean `main`
- base authority: `019f3c406400f4ecb07b864349369981d4654513`
- merged successor runtime SHA-256: `9327d3fef6b1ba2ea8e9d380338e69e6084388b0d365019af3505e8a6a880834`
- implementation review SHA-256: `fe7bd30cc8afdaa318d09a65748f2ae2d214d7c42f83416b666f1da9d8580a1a`
- implementation record SHA-256: `6815a8d3b6a7eb5e88212fd0e280cbfc686f378ab0c98f18e1a05e0de0681b27`
- frozen experiment design SHA-256: `888bf0a25a974ba2c62892bc999fe0c9f23d2cf845bcd2542c67e2c9bc4ccf03`

Current merged evidence outranks historical authorization precedent.

## Design-Only Paths

Exactly five paths belong to this tranche:

1. authorization-design producer
2. focused authorization-design test
3. producer-owned authorization-design JSON
4. authorization-design report
5. this runbook

No notebook belongs to this tranche.

## Static Validation

The producer must deterministically generate and validate the design JSON.

Validate changed mutable Python with governed Ruff formatting/lint and focused mypy.

Run focused authorization-design pytest, full repository pytest, and the authoritative immutable-lineage repository typecheck gate.

Use `git diff --check`.

Before commit, prove the exact five-path candidate boundary and staged/worktree Git-blob byte identity.

Do not substitute raw repository-wide Ruff for the governed changed-Python gate.

## Frozen Future Transaction

A future authorization issuer must preserve:

- transaction-bound executable architecture
- A/B/C request order `A,B,C,B,C,A,C,A,B`
- 899 prompt tokens per condition
- 3 observations per condition
- fresh worker per observation
- maximum 9 requests, 9 loads, 9 starts
- zero hidden retries
- zero replacement observations
- zero external network requests
- zero benchmark-trajectory requests
- zero spend
- 32 maximum output tokens per request
- T4 x2
- Internet Off
- credentials/customer data prohibited
- fresh durable platform observation before Save & Run All
- dynamic SHA-256 human retype
- terminal single-use authority

## Decision Gate

A must reproduce 0/3 before B/C mechanistic inference is permitted.

Mixed 1/3 or 2/3 results produce no mechanistic claim.

The four stable A=0/3 states are frozen in the design record. Any runtime/token/worker/cold-state/budget/teardown/cleanup invariant failure produces `DIAGNOSTIC_INVALID`.

## Prohibited Actions

This design tranche must not:

- issue live authorization
- generate a live governed executable
- create authorization-specific Kaggle inputs
- create authorization producer notebooks
- persist a live platform observation
- execute Save & Run All
- load the model
- start a worker
- perform a model request
- alter the frozen A/B/C design
- search thresholds
- remediate runtime behavior
- requalify P5/P6

## Completion State

Required static state:

- `status=DESIGN_FROZEN_NOT_EXECUTED`
- `live_authorization_issued=false`
- `runtime_execution_authorized=false`
- `governed_executable_generated=false`
- `platform_observation_persisted=false`
- `kaggle_execution_performed=false`
- `model_requests_performed=0`
- `model_loads_performed=0`
- `worker_starts_performed=0`

## Next Gate

`IMPLEMENT_AND_MERGE_P4_P5_TOKEN_COUNT_MATCHED_CONTEXT_STRUCTURE_DIFFERENTIAL_EXECUTION_AUTHORIZATION_ISSUER_V1`
