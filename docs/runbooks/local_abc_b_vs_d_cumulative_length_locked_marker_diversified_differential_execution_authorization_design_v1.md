# Runbook — B-vs-D Cumulative-Length-Locked Marker-Diversified Differential Execution Authorization Design V1

## Purpose

Operate the static authorization-design tranche only. This runbook does not grant live authority and does not permit Kaggle, GPU, worker, model-load, or model-request execution.

## Repository Preconditions

- branch: `feat/local-abc-b-vs-d-cumulative-length-locked-marker-diversified-differential-execution-authorization-design-v1`
- frozen base/implementation merge: `a24eedc9d7a65756affc9cde224acdc80fdf7313`
- current B-vs-D design is frozen
- current B-vs-D implementation is merged and `IMPLEMENTED_NOT_EXECUTED`
- no B-vs-D authorization issuer exists
- no live B-vs-D authority exists
- no B-vs-D transaction exists

## Tranche Paths

Authored source:

`src/auragateway/local_abc/b_vs_d_cumulative_length_locked_marker_diversified_differential_execution_authorization_design_v1.py`

Focused test:

`tests/unit/local_abc/test_b_vs_d_cumulative_length_locked_marker_diversified_differential_execution_authorization_design_v1.py`

Producer-owned generated record:

`benchmarks/local_abc/auragateway_b_vs_d_cumulative_length_locked_marker_diversified_differential_execution_authorization_design_v1.json`

Report:

`docs/reports/AuraGateway_B_Vs_D_Cumulative_Length_Locked_Marker_Diversified_Differential_Execution_Authorization_Design_V1.md`

Runbook:

`docs/runbooks/local_abc_b_vs_d_cumulative_length_locked_marker_diversified_differential_execution_authorization_design_v1.md`

The generated JSON is owned by the authorization-design producer and must not be hand-edited.

## Static Design Commands

Generate the deterministic design record:

`python -m auragateway.local_abc.b_vs_d_cumulative_length_locked_marker_diversified_differential_execution_authorization_design_v1 generate --repo-root .`

Validate the deterministic design record:

`python -m auragateway.local_abc.b_vs_d_cumulative_length_locked_marker_diversified_differential_execution_authorization_design_v1 validate --repo-root .`

The validator must confirm the frozen design authority, merged runtime/review/record identities, the B-vs-D semantic contract, implementation semantic closure, base-commit ancestry, and deterministic generated-record equality.

## Required Focused Gates

Run governed formatting/lint on the authored Python paths before focused type/test validation according to the repository's current Workflow V23 commands.

Then require:

- Python compilation of authored design source
- focused mypy on authored design source and focused test
- deterministic `generate`
- deterministic `validate`
- focused authorization-design pytest
- post-gate deterministic `validate`

Repository-authoritative wide gates remain required before staging. Raw repository-wide Ruff or mypy must not replace the repository's immutable-lineage-aware validators.

## Git Custody

Before commit:

- candidate boundary must be exactly the five intended paths
- generated record must match deterministic rendering
- identity-bearing staged bytes must equal validated worktree bytes
- `git diff --check` must pass
- no unexpected tracked or untracked remainder may enter the tranche
- stage exact paths only; do not use `git add .`

## Forbidden During This Runbook

Do not:

- implement the issuer
- issue live authority
- synthesize the human authorization challenge/retype
- generate a live transaction-bound executable
- run Kaggle
- Save & Run All
- load a model
- start a worker
- perform a model request
- execute B-vs-D
- replay PR #261 or PR #267 authority
- alter B or D
- alter request order
- alter generation controls
- search repetition thresholds
- add another discriminator
- requalify P5 or P6
- run the variance pilot
- authorize or execute final measured A/B/C

## Acceptance State

The tranche is complete only when the design record is deterministically generated and validated, the exact authorization scope is frozen, all five intended paths pass repository-authoritative validation/custody, the PR merges, and post-merge reconciliation confirms no live authority or execution occurred.

Expected state after merge:

- `status=DESIGN_FROZEN_NOT_EXECUTED`
- `live_authorization_issued=false`
- `runtime_execution_authorized=false`
- `governed_executable_generated=false`
- `platform_observation_persisted=false`
- `model_requests_performed=0`
- `model_loads_performed=0`
- `worker_starts_performed=0`

## Next Gate

`IMPLEMENT_AND_MERGE_B_VS_D_CUMULATIVE_LENGTH_LOCKED_MARKER_DIVERSIFIED_DIFFERENTIAL_EXECUTION_AUTHORIZATION_ISSUER_V1`
