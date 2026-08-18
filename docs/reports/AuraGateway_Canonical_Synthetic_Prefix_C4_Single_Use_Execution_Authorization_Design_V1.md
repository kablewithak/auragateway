# AuraGateway Canonical Synthetic Prefix C4 — Single-Use Execution Authorization Design V1

## Status

`DESIGN_FROZEN_NOT_EXECUTED`

This tranche freezes the static control-plane design for a future single-use C4
execution authorization. It does not implement an issuer, issue live authority,
generate a governed executable, execute Kaggle, load a model, start a worker, or
perform a model request.

## Frozen Authorization Scope

`CANONICAL_SYNTHETIC_PREFIX_C4_BEHAVIORAL_QUALIFICATION_V1`

Architecture:

`TRANSACTION_BOUND_EXECUTION_ARTIFACT`

## Bound Current Authorities

The deterministic design record binds the exact merged C4 lineage:

- qualification request SHA-256:
  `0177ad9f81aac2f4f85ab7703cedb3f17a54cab4f47c414a31691a6e21e2a884`
- qualification review SHA-256:
  `ff1ecb531db85cfacab26db9f546fdc981292dd3feb2da6934a3e74c712286bc`
- reusable-prefix identity receipt SHA-256:
  `e6ae9dfac5653416ae02d5a8c649faa2b19a3a42529de2b1822a584335933835`
- merged successor runtime SHA-256:
  `d2cc4f38823a0133345279ed0257bf726ebcf8190ef0985620e76815700d4e82`
- implementation review SHA-256:
  `d5bbb90fbf171ad3c38e713b9aa71e2fd6dbc39254236933dcdf446e824d9452`
- implementation record SHA-256:
  `7e5d102ed485279f0d8efd344529ec92b96e97a858b68652518a0472aeb9665a`
- implementation source SHA-256, transitively bound by the review:
  `233a38bdbe6631547811bcf135ba0e40470d9e04b1e71268aef11c6e34a788f4`
- focused implementation test SHA-256, transitively bound by the review:
  `8c27d55ed3464c9214c28603aa4e9f733fcafe6830b8b44efbe5e97d6a432c61`
- implementation merge/base main commit:
  `9785f9f931bfa5bdd2d0bd97881759b5610eafa6`

The design validator uses ancestry semantics for the frozen base commit.

## Frozen C4 Contract

The future governed transaction remains exactly three independent observations:

1. fresh worker;
2. zero cached-prefix baseline;
3. one exact canonical request;
4. response and worker-health evidence;
5. teardown;
6. repeat until three observations are complete.

Frozen request identities:

- canonical corpus:
  `CANONICAL_SYNTHETIC_PREFIX_CORPUS_V1`
- canonical corpus SHA-256:
  `140e8157da883e07f2d76d4f516ec2beec961fefb639b8509cc8f3a6239d14e9`
- full prompt token count: `899`
- full prompt token SHA-256:
  `f009b149b0b8ccf08a423346e1736be81927095907b5221e070e59ffc6d87f4c`
- reusable-prefix token count: `880`
- reusable-prefix token SHA-256:
  `f29af54ca46249fa63c7fd89da44ca375d64f183f8d463b3a43678318890dfb1`
- canonical request-payload SHA-256:
  `a888c17ed8e82360fdd46d0bb6833db9db2dc3fbbfb14d861f7063b271063788`
- canonical expected object:
  `{"probe":"exact-runtime-p5-p6","value":1}`

The exact response contract requires valid JSON, root object, exact key set,
duplicate-key rejection, typed integer value `1`, exact probe value, no fences or
surrounding prose, response completion, healthy worker, transport success, and
`finish_reason == "stop"`.

Healthy behavioral violations complete all three scheduled observations.
Execution-invalidating setup, authority, runtime, worker, transport, budget,
teardown, cleanup, or evidence-custody failures stop without hidden retry or
replacement.

Terminal behavioral states remain:

- `QUALIFIED`: complete interpretable evidence and exact `3/3` pass.
- `NOT_QUALIFIED`: complete interpretable execution with at least one healthy
  contract violation.
- `INVALID_EXECUTION`: a control-plane or execution invariant prevents valid
  qualification.

There is no threshold relaxation.

## Frozen Budgets

Maximums:

- Kaggle sessions: `1`
- Save & Run All actions: `1`
- runtime installation attempts: `1`
- runtime import-closure probes: `1`
- model loads: `3`
- worker starts: `3`
- model requests: `3`
- worker teardowns: `3`
- output tokens per request: `32`
- hidden retries: `0`
- replacement requests: `0`
- external network requests: `0`
- benchmark trajectory requests: `0`
- external spend: `0`

Runtime counters count attempts rather than successful completion. Kaggle-session
and Save & Run All budgets remain platform-enforced and must be reconciled later.

## Human Authorization Boundary

A later issuer may create live authority only after a fresh human-controlled:

`RETYPE_DYNAMIC_SHA256_CHALLENGE`

The exact retype must bind the complete authorization intent. The runtime, model,
issuer, and assistant may not synthesize the confirmation.

This design performs no live confirmation and issues no authority.

## Platform and Transport Boundary

Required future platform policy:

- accelerator: `T4_X2`
- allocated GPU count: `2`
- Internet: `Off`
- credentials: prohibited
- customer data: prohibited
- external network access: prohibited

A transaction-bound executable must exist before a fresh durable platform
observation is recorded. The receipt must exist before the single Save & Run All.

Authorization-specific Kaggle inputs, authorization producer notebooks, manual
confirmation JSON, and runtime authorization filename discovery remain prohibited.

## Single-Use and Acceptance Boundary

Attempted execution terminalizes authority. A terminal authorization is not
reusable and unchanged replay is unauthorized.

Runtime observation is not repository acceptance. A later reconciliation must
verify authorization lifecycle, evidence identity, saved-version identity,
platform budgets, runtime identity, and the accepted C4 terminal state.

Only repository-accepted C4 qualification may advance to the controlled-local
P5/P6 successor, which must derive from this C4 runtime lineage.

## Evidence and Privacy Boundary

Expected evidence ZIP:

`ag-c4-canonical-prefix-qual-evidence-v1.zip`

Stable evidence includes the request-results, decision, token-identity journal,
worker teardown, cleanup, failure, summary, human report, bundle manifest, and
runtime readiness/environment identities.

Raw prompts and raw model outputs are not retained. Credentials and customer data
remain prohibited.

## Non-Claims

This design does not establish:

- live execution authority;
- C4 qualification;
- a successful future model response;
- P5 requalification;
- P6 requalification;
- final A/B/C effects;
- a prefix-cache defect;
- historical root cause;
- general model reliability;
- production readiness.

## Next Gate

After merge and post-merge reconciliation only:

`IMPLEMENT_AND_MERGE_CANONICAL_SYNTHETIC_PREFIX_C4_SINGLE_USE_EXECUTION_AUTHORIZATION_ISSUER_V1`
