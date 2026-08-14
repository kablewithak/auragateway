# AuraGateway P4/P5 Cache-Context Repetition Differential Execution Authorization Design V1

## Status

`DESIGN_FROZEN_NOT_EXECUTED`

This tranche freezes the control-plane contract for one future governed execution
of the merged 1x-versus-24x cache-context repetition differential. It does not
issue live authority, generate the governed executable, or execute Kaggle.

## Bound implementation authority

Implementation merge commit:

`658a21516fa6b1cc72bd53c2c65e51aae88b4d79`

Merged successor runtime SHA-256:

`dfa0e7ea48eaf21dd6d3faf97b0440dda19817dec18de7c17d720c9185569a4b`

Implementation review SHA-256:

`6bf7595e9dda3793f94bf866e0feff8db31cfe2c4c9cd7e3f4941c973a4ea2a4`

Implementation record SHA-256:

`31628aef52b292236bbaf9a787fd1f47ca3751a1416cf916b51fc354258e4a6c`

Frozen repetition-design record SHA-256:

`1dc00c0bc36a1979291078b16c7b54ed502385bb62a53c6043d255c5fcf4fa00`

## Authorization architecture

Architecture:

`TRANSACTION_BOUND_EXECUTION_ARTIFACT`

Scope:

`P4_P5_CACHE_CONTEXT_REPETITION_DIFFERENTIAL_V1`

The eventual live authorization must bind the merged implementation lineage,
exact runtime/model contract, generator contract, runtime payload, execution
budget, frozen repetition-differential contract, required platform policy,
durable platform-observation contract, and live authorization window.

The static repository runtime is not itself an authorized executable.

## Human authorization

Live issuance requires a fresh dynamic SHA-256 challenge and exact human retype.
The confirmation binds one exact authorization intent.

Maximum confirmation age: 15 minutes.

Default authorization window: 180 minutes.

Maximum authorization window: 240 minutes.

Human authorization may not be synthesized by the runtime, model, issuer, or
assistant.

## Frozen repetition differential

Variable under test:

`CACHE_CONTEXT_REPETITION_COUNT`

Conditions:

- `CONTROL_1X`: one cache-context repetition, three observations.
- `TREATMENT_24X`: 24 cache-context repetitions, three observations.

Frozen request order:

`CONTROL_1X, TREATMENT_24X, TREATMENT_24X, CONTROL_1X, CONTROL_1X, TREATMENT_24X`

Every observation requires a fresh worker process and a zero cached-prefix
baseline before the model request.

The 24x treatment must retain the historical failed request identity:

- token count: 899
- token SHA-256:
  `6b34448d083e68826cae84c0675876c18d7a70fab53299860b78f2a5a18922b0`
- payload SHA-256:
  `b038763a5a2cb09f0a565dd7d11ac959c42c9c9a53f0f2d5e384edb6531c3a8e`

No post-hoc 2/3 interpretation is permitted.

Frozen decision states remain:

- 1x 3/3 exact and 24x 0/3 exact:
  `LONG_REPEATED_CONTEXT_NECESSITY_SUPPORTED`
- 1x 0/3 exact and 24x 0/3 exact:
  `REPETITION_NOT_NECESSARY`
- 1x 3/3 exact and 24x 3/3 exact:
  `REGRESSION_NOT_REPRODUCED`
- unstable/mixed 1x:
  `CONTROL_NOT_RELIABLE`
- stable 1x 3/3 with mixed 24x:
  `NON_DETERMINISTIC_OR_AMBIGUOUS`
- runtime, worker, identity, cold-state, budget, teardown, or cleanup invariant
  failure:
  `DIAGNOSTIC_INVALID`

The design does not authorize threshold search, assistant/topology
discrimination, runtime remediation, P5/P6 requalification, or measured A/B/C
execution.

## Execution budget

One future governed transaction permits at most:

- 1 Kaggle session
- 1 Save & Run All
- 1 runtime-install attempt
- 1 runtime import-closure probe
- 6 model requests
- 6 model loads
- 6 worker starts
- 0 hidden retries
- 0 replacement workers
- 0 external network requests
- 0 benchmark-trajectory requests
- 0 external spend

The 6/6/6 request/load/worker budget is required because the frozen experiment
uses one fresh worker process for each of six observations.

## Platform boundary and forward control

Required platform policy:

- accelerator: T4 x2
- allocated GPUs: 2
- Internet: Off
- external network access: prohibited
- credentials: prohibited
- customer data: prohibited

The durable control remains:

`PERSIST_DURABLE_OBSERVATION_BEFORE_SAVE_AND_RUN_ALL`

After the transaction-bound artifact is generated and before the single Save &
Run All, a durable receipt must exist and bind:

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

`ag-p4-p5-cache-context-repetition-differential-evidence-v1.zip`

The failure-safe pre-request token identity journal remains:

`pre_request_token_identity_journal_v1.json`

Raw prompts and raw model outputs remain prohibited.

Terminal evidence must bind transaction identity, durable platform observation,
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

## Non-claims

This design does not establish the 1x-versus-24x behavioral result, an exact
causal threshold, context length as root cause, prefix-cache defect, P5 success,
P6 success, live execution authority, Kaggle execution, measured A/B/C support,
or production readiness.

## Next gate

`IMPLEMENT_AND_MERGE_P4_P5_CACHE_CONTEXT_REPETITION_DIFFERENTIAL_EXECUTION_AUTHORIZATION_ISSUER_V1`
