# AuraGateway P4/P5 Composition Remediation Execution Authorization V1

## Status

`IMPLEMENTED_NOT_ISSUED`

This tranche implements the single-use transaction-bound authorization issuer
for one future governed full remediated P5/P6 confirmation. It does not issue
live authority during implementation and does not execute Kaggle.

## Bound authorities

- authorization-design merge: `788305abee1f7f4bae2d61d88009cf3f3a5f33a9`
- authorization-design record SHA-256: `8eefe8e9d343fc20fcab4b868d623f546478787c0e57b32b836f6b879f7265b4`
- remediation implementation merge: `f5701274037162ab9ff8f0627a544ac76d9c1b7b`
- remediated runtime SHA-256: `aa0631ef5bc7b13c6d0f4a00078b6b35bc274147fc0847965dc000f732adc7ff`
- implementation review SHA-256: `feecd56b5688bffb2a79369bd28f351756c8ae78f3f1c4c38dfd9365831eb76c`
- implementation record SHA-256: `681b0463488f50d48c43b2256a0a50f0f276f10cc46c479db65c0c6e385970f8`

## Issuance contract

Live issuance is allowed only from synchronized clean `main` after this issuer
has been merged. A fresh SHA-256 challenge binds the exact authorization intent
and must be retyped by the operator within 15 minutes. The transaction ID is
SHA-256 over canonical authorization-body bytes.

One live authorization binds the exact runtime/model contract, six-request full
P5/P6 qualification, 6 model requests, 3 worker starts, 3 model loads, zero
hidden retries, T4 x2, Internet Off, no credentials, and no customer data.

## Durable platform observation

After the transaction-bound notebook is generated, the issuer does **not** mark
the run ready for Save & Run All. The separate
`record-platform-observation` transition persists
`auragateway_p4_p5_composition_remediation_platform_observation_v1_live.json`.

The receipt binds transaction ID, authorization identity, manifest identity,
platform observation timestamp, accelerator, allocated GPU count, Internet
state, and capability source. It is explicitly not a runtime authorization
input. Its successful persistence is the operator gate before the single Save &
Run All.

## Runtime admission

The generated wrapper validates canonical authorization bytes, transaction
identity, exact lineage, runtime payload identity, execution budget, full
qualification contract, authorization window, and machine-observable two-GPU
topology before executing the embedded remediated runtime.

## Terminalization

Every attempted execution terminalizes the authority. Terminal authority is not
reusable. A PASSED outcome requires the durable platform-observation receipt.
Failure and diagnostic-invalid terminalization remain possible even if the
platform receipt or expected evidence ZIP is missing, so governance does not
lose the ability to close a bad attempt.

## Current state

- live authorization issued: false
- runtime execution authorized: false
- platform observation persisted: false
- Kaggle execution performed: false
- model requests performed: 0
- model loads performed: 0
- worker starts performed: 0
- Case C authorized: false

## Next gate

`MERGE_THEN_ISSUE_FRESH_P4_P5_COMPOSITION_REMEDIATION_EXECUTION_AUTHORIZATION_V1`
