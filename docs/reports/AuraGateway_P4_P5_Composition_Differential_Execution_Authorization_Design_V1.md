# AuraGateway P4/P5 Composition Differential Execution Authorization Design V1

## Purpose

Freeze the smallest execution-authorization contract required to run the merged
P4/P5 message-composition differential exactly once.

## Current authority

Implementation merge commit:

`96dea44afa28e1b61c68eb0eccfc91d312bb89e0`

Successor runtime:

`4711f94031bc65ae159dab14412d99cfbd9ecee01b5a2d7d2fd7a2c2b09d7db7`

Implementation review:

`523f42b32d76ae357313f009b548703ea2da8fd9f6496cf6adb7cc50ad4ec655`

Implementation record:

`8b2b11f367b60272323cb9e6269cbb09e597063d03467207798c96b25e79b1b1`

Current execution state remains false.

## Selected architecture

`TRANSACTION_BOUND_EXECUTION_ARTIFACT`

This deliberately reuses the repository's accepted successor authorization
architecture rather than reintroducing authorization-specific Kaggle inputs or
control-producer notebooks.

## Authorization lineage binding

Future live authority is scope-bound to
`P4_P5_COMPOSITION_DIFFERENTIAL_V1`.

The canonical authorization must bind the merged authorization-design identity,
merged issuer commit, merged differential implementation authorities, exact
runtime/model contract, generator/runtime-payload identities, execution budget,
experiment contract, required platform policy, and live authorization window.

The fresh SHA-256 operator challenge must confirm that exact authorization
intent rather than an unbound generic challenge.

## Governed execution

The future transaction is limited to:

- A/B message-composition differential only;
- request order `A,B,B,A,A,B`;
- three repetitions per case;
- six model requests total;
- one worker;
- one model load;
- zero hidden retries.

The authorization cannot expand to Case C or runtime remediation.

## Human boundary

Issuance requires a fresh dynamic SHA-256 challenge and exact operator retype.

Static implementation, model output, runtime state, or assistant output cannot
satisfy the human confirmation boundary.

## Platform boundary

The authorization binds required T4 x2 / Internet Off policy.

The fresh platform observation occurs after transaction-bound artifact
generation and before the single Save & Run All.

This removes circular identity dependence while preserving runtime topology
verification.

## Single-use boundary

Canonical authorization bytes define the transaction ID.

Every execution attempt terminalizes the authority.

Multiple executions observed for one transaction invalidate governed
acceptance.

Runtime anti-replay is not claimed.

## Privacy and evidence

Credentials and customer data are prohibited.

Raw prompts and raw outputs are not retained.

Metadata-safe evidence is preserved under the existing differential evidence
contract.

## Design state

`status=DESIGN_FROZEN_NOT_EXECUTED`

`live_authorization_issued=false`

`runtime_execution_authorized=false`

`model_requests_performed=0`

`differential_notebook_generated=false`

## Next gate

`IMPLEMENT_AND_MERGE_P4_P5_COMPOSITION_DIFFERENTIAL_EXECUTION_AUTHORIZATION_ISSUER_V1`
