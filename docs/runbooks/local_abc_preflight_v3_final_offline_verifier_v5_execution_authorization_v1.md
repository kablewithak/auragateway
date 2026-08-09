# Runbook: Final Offline Verifier V5 Execution Authorization V1

## Purpose

Govern one short-lived execution authorization for the already merged Final
Offline Verifier V5 implementation.

The issuer is a repository control plane. It does not execute Kaggle itself.

## Bound implementation

Feature commit:

`7760ee785ec11d6c85d8d2d2d2a20b59a2ef9e23`

Merge commit:

`a0a21c648e881c7eb733967b42ee6f08cbcbb48a`

The issuer binds all eight accepted V5 implementation artifacts by SHA-256 and
size.

## Repository phase

Before this issuer is merged:

`runtime_execution_authorized=false`

`next_kaggle_execution_authorized=false`

Do not create the live authorization JSON on the feature branch.

## Issue preconditions

Issuance requires:

- issuer merged to synchronized clean `main`;
- exact issuer merge commit supplied to the command;
- merged V5 implementation still present at exact bound identities;
- V5 implementation validator passes again at issuance;
- semantic/evidence invariants remain zero-drift;
- no existing authorization, consumption, or abandonment artifact;
- explicit operator confirmation of fresh Kaggle T4 x2 with Internet off.

The exact confirmation phrase is:

`I_CONFIRM_FRESH_KAGGLE_T4_X2_INTERNET_OFF_AND_AUTHORIZE_ONE_FINAL_OFFLINE_VERIFIER_V5_EXECUTION`

These Kaggle environment facts are operator attestations. The local issuer does
not claim to observe remote Kaggle hardware.

## Hard limits

One Kaggle session.
One runtime-install attempt.
One native-import closure probe.
Zero model loads.
Zero worker starts.
Zero model requests.
Zero benchmark trajectories.
Zero external network requests.
Zero hidden retries.
Zero external spend.

Default authorization lifetime: 180 minutes.
Maximum authorization lifetime: 240 minutes.

## Commands after issuer merge

Generate/validate repository issuer record before commit:

`python -m auragateway.local_abc.preflight_v3_exact_runtime_offline_compatibility_v5_execution_authorization_v1 generate-record --repo-root .`

`python -m auragateway.local_abc.preflight_v3_exact_runtime_offline_compatibility_v5_execution_authorization_v1 validate-implementation --repo-root .`

After merge, issue only after the operator has actually prepared fresh Kaggle
T4 x2 with Internet off.

The live authorization, consumption, and abandonment files are transient
operator-state artifacts. Do not stage them into the repository.

## Expected execution evidence

`input_validation.json`

`probe_records.json`

`verification_summary.json`

`evidence_manifest.json`

`auragateway_preflight_v3_exact_runtime_offline_compatibility_evidence_v5.zip`

## Terminal lifecycle

A PASSED or FAILED consumption requires both the saved Kaggle version ID and
evidence ZIP SHA-256.

INTERRUPTED may omit both when no saved/evidence artifact exists.

Once consumed or abandoned, the authority is terminal and non-reusable.

## Non-claims

This issuer does not prove exact-runtime compatibility.

It does not authorize model execution, P5/P6, a pilot, or measured A/B/C.
