# AuraGateway P4/P5 Composition Remediation Execution Authorization Design V1

## Status

`DESIGN_FROZEN_NOT_EXECUTED`

This tranche freezes the control-plane contract for one future governed full
P5/P6 confirmation of the merged composition remediation. It does not issue
live authority, generate the governed executable, or execute Kaggle.

## Bound implementation authority

Implementation merge commit:

`f5701274037162ab9ff8f0627a544ac76d9c1b7b`

Merged remediated runtime SHA-256:

`aa0631ef5bc7b13c6d0f4a00078b6b35bc274147fc0847965dc000f732adc7ff`

Implementation review SHA-256:

`feecd56b5688bffb2a79369bd28f351756c8ae78f3f1c4c38dfd9365831eb76c`

Implementation record SHA-256:

`681b0463488f50d48c43b2256a0a50f0f276f10cc46c479db65c0c6e385970f8`

## Authorization architecture

Architecture:

`TRANSACTION_BOUND_EXECUTION_ARTIFACT`

Scope:

`P4_P5_COMPOSITION_REMEDIATION_CONFIRMATION_V1`

The eventual live authorization must bind the merged implementation lineage,
exact runtime/model contract, generator contract, runtime payload, execution
budget, full qualification contract, required platform policy, and live
authorization window.

The static repository runtime is not itself an authorized executable.

## Human authorization

Live issuance requires a fresh dynamic SHA-256 challenge and exact human
retype. The confirmation binds one exact authorization intent.

Maximum confirmation age: 15 minutes.

Default authorization window: 180 minutes.

Maximum authorization window: 240 minutes.

Human authorization may not be synthesized by the runtime, model, issuer, or
assistant.

## Full P5/P6 confirmation contract

This is not another standalone A/R composition diagnostic. The accepted
composition differential is already the baseline.

The governed confirmation runs the full remediated P5/P6 trajectory with six
structured request roles:

`BASE_COLD, BASE_WARM, NEGATIVE_PREFIX, POST_RESET_COLD, CROSS_WORKER_COLD, WORKER1_RETENTION`

Acceptance requires all six structured requests to return the exact canonical
object, P5 state `PASS`, P6 state `PASS`, cache-specific proof, P6 isolation
proof, exact action budgets, teardown `PASSED`, and scratch cleanup `PASSED`.

The qualification must also preserve the failure-safe
`pre_request_token_identity_journal_v1.json` evidence.

Case C remains unauthorized.

## Execution budget

One future governed transaction permits at most:

- 1 Kaggle session
- 1 Save & Run All
- 1 runtime-install attempt
- 1 runtime import-closure probe
- 6 model requests
- 3 model loads
- 3 worker starts
- 0 hidden retries
- 0 replacement workers
- 0 external network requests
- 0 benchmark-trajectory requests
- 0 external spend

## Platform boundary and forward control

Required platform policy:

- accelerator: T4 x2
- allocated GPUs: 2
- Internet: Off
- external network access: prohibited
- credentials: prohibited
- customer data: prohibited

The prior console-only observation gap is closed by the frozen control:

`PERSIST_DURABLE_OBSERVATION_BEFORE_SAVE_AND_RUN_ALL`

After the transaction-bound artifact is generated and before the single Save &
Run All, a durable receipt must already exist and bind:

- transaction ID
- platform observation timestamp
- accelerator
- allocated GPU count
- Internet state
- capability source

The receipt is not mounted as runtime authorization input. Runtime admission
still requires a machine-observable topology check. Failure to persist the
receipt blocks execution.

## Transport topology

Authorization-specific Kaggle inputs: 0.

Authorization producer notebooks: 0.

Manual confirmation JSON files: 0.

Permitted Kaggle input roles remain only `durable_runtime` and
`model_snapshot`.

## Evidence and terminalization

Expected runtime evidence ZIP:

`ag-p5-p6-transaction-bound-evidence-v1.zip`

Raw prompts and raw model outputs remain prohibited.

Terminal evidence binds transaction identity, durable platform observation,
saved-version identity, and evidence identity.

Attempted execution terminalizes authority. Terminal authority is never
reusable. Multiple observed executions invalidate governed acceptance and
require reconciliation.

Runtime anti-replay and malicious-operator resistance are not claimed.

## Current state

- live authorization issued: false
- runtime execution authorized: false
- governed executable generated: false
- durable platform observation persisted: false
- Kaggle execution performed: false
- model requests performed: 0
- model loads performed: 0
- worker starts performed: 0
- Case C authorized: false

## Non-claims

This design does not establish remediation success, P5 success, P6 success,
live execution authority, Kaggle execution, or production readiness.

## Next gate

`IMPLEMENT_AND_MERGE_P4_P5_COMPOSITION_REMEDIATION_EXECUTION_AUTHORIZATION_ISSUER_V1`
