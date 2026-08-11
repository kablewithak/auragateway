# ADR: P4/P5 Composition Differential Execution Authorization Design V1

Date: 2026-08-12

Status: Accepted for design-tranche review

## Context

The merged P4/P5 composition differential isolates `MESSAGE_COMPOSITION_ONLY`
using six fixed requests in order `A,B,B,A,A,B`.

Merged implementation authority is commit:

`96dea44afa28e1b61c68eb0eccfc91d312bb89e0`

Merged successor runtime SHA-256:

`4711f94031bc65ae159dab14412d99cfbd9ecee01b5a2d7d2fd7a2c2b09d7db7`

The implementation is merged but unexecuted.

## Decision

Reuse AuraGateway's accepted transaction-bound execution-artifact architecture.

The future live authorization will be converted into canonical authorization
bytes. Their SHA-256 becomes the transaction identity. A deterministic
post-authorization generator will bind that authorization to the exact
successor runtime and produce the transient governed executable.

The static repository runtime cannot authorize itself and is not the governed
execution artifact.

## Authorization payload binding

The future canonical authorization must bind:

- scope `P4_P5_COMPOSITION_DIFFERENTIAL_V1`;
- this authorization-design record SHA-256 after merge;
- the merged issuer commit;
- the merged differential implementation commit and authority hashes;
- the exact runtime/model contract;
- the generator contract and runtime-payload identities;
- the 1-load / 1-worker / 6-request execution budget;
- the frozen A/B experiment contract;
- the required platform policy;
- the live authorization window.

The dynamic operator confirmation must bind the exact authorization intent.
A valid confirmation for different authority bytes is not transferable.

## Human authorization

Live authority requires a fresh dynamic SHA-256 challenge that the operator
must retype exactly.

The runtime, model, issuer, or assistant may not synthesize human confirmation.

Default authority lifetime is 180 minutes and may not exceed 240 minutes.
Operator confirmation must be no more than 15 minutes old when authority is
issued.

## Execution budget

One governed transaction permits at most:

- one Kaggle session;
- one Save & Run All;
- one runtime-install attempt;
- one runtime import-closure probe;
- one model load;
- one worker start;
- six model requests;
- zero hidden retries;
- zero replacement workers;
- zero external network requests;
- zero benchmark-trajectory requests;
- zero external spend.

## Platform sequence

Pre-issuance Kaggle observation is not required.

The required platform policy is bound by the authorization. After the final
transaction-bound executable is generated, the operator must freshly observe
T4 x2 with Internet Off before the single Save & Run All.

The observation is not mounted as runtime input. Runtime admission still checks
machine-observable topology.

## Differential boundary

Case A is exactly `system,user`.

Case B is exactly `system,user,assistant,user`.

Order is exactly `A,B,B,A,A,B`.

Decision mapping remains frozen:

- A 3/3 and B 0/3: `COMPOSITION_REGRESSION_SUPPORTED`
- A 3/3 and B 3/3: `COMPOSITION_HYPOTHESIS_NOT_REPRODUCED`
- A not 3/3: `SIMPLE_CONTROL_NOT_RELIABLE`
- otherwise: `NON_DETERMINISTIC_OR_AMBIGUOUS`

A mixed result does not authorize Case C. Case C requires a separately designed
and separately authorized transaction.

No runtime remediation is authorized by this design.

## Transport boundary

Authorization-specific Kaggle inputs: 0.

Authorization producer notebooks: 0.

Manually constructed confirmation JSON files: 0.

Permitted Kaggle input roles remain only durable runtime and model snapshot.

## Lifecycle

Every attempted execution terminalizes authority.

Terminal authority is never reusable.

A second observed execution for the same transaction invalidates governed
acceptance and requires reconciliation. Runtime anti-replay and
malicious-operator resistance are not claimed.

Primary failures must not be masked by teardown, cleanup, evidence-packaging,
or terminalization failures.

## Evidence

Raw prompts and raw model outputs are not retained.

The expected governed evidence artifact is:

`ag-p4-p5-composition-differential-evidence-v1.zip`

Terminal evidence binds transaction identity, platform observation, saved
version identity, and evidence identity.

The authorization remains terminalizable when the expected evidence ZIP is
missing.

## Non-claims

This design does not:

- implement an issuer;
- issue live authority;
- generate the governed executable;
- execute Kaggle;
- load a model;
- start a worker;
- perform a model request;
- establish the composition hypothesis;
- establish Case C;
- authorize runtime remediation.

## Next gate

`IMPLEMENT_AND_MERGE_P4_P5_COMPOSITION_DIFFERENTIAL_EXECUTION_AUTHORIZATION_ISSUER_V1`
