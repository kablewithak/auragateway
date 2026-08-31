# ADR: Final-342 Execution Manifest Post-Commit Custody V1

Date: 2026-08-31

## Status

Proposed for acceptance.

## Context

G11.12A deterministically materialized and committed the frozen final-342 execution-manifest
subject. The accepted G11.3A Git-custody model deliberately prevented the manifest from embedding
the SHA of the commit that first contains its own bytes, because that would create recursive
identity.

The exact first containing commit now exists:

`078c1da32fe7c1ee8ff5a8661e5f38e588782abc`

Its direct parent is the accepted source subject:

`fcf403a1c31e26a2cdf3f682a8878db01338a13d`

The source subject does not contain the final manifest path.

## Decision

Bind a separate deterministic custody receipt to all four identities required by G11.3A:

- manifest semantic SHA-256:
  `11b4ef75a6a44df51b445c4421290e41ee0994a6143d2e2d8bc034130f35129b`;
- manifest file SHA-256:
  `74ce9ada48c2a788ddba9c4cbf2eeba61ab68937e04916b044b567c9b239cc0c`;
- source-subject commit:
  `fcf403a1c31e26a2cdf3f682a8878db01338a13d`;
- first-containing commit:
  `078c1da32fe7c1ee8ff5a8661e5f38e588782abc`.

The receipt also binds the exact manifest Git blob
`2c733e930b88bca5f8ad0730d6828a88f8655e14` and the first-containing tree
`64750c2ef4ee19add4d38ba916d3d0832e844bef`.

The validator proves:

1. the first-containing commit is directly based on the accepted source subject;
2. the source subject did not already contain the final manifest;
3. the first-containing commit contains exactly the frozen manifest bytes;
4. the current manifest still matches those exact bytes; and
5. the first-containing commit remains an ancestor of the validation HEAD.

## Freeze promotion

Successful custody validation promotes:

```text
MANIFEST_SUBJECT_BYTES_FROZEN=true
POST_COMMIT_CUSTODY_COMPLETE=true
REPOSITORY_EXECUTION_MANIFEST_FROZEN=true
REPOSITORY_FREEZE_GATE_PROMOTED=true
```

This does **not** issue execution authority.

```text
FINAL_MEASURED_ABC_EXECUTION_AUTHORIZED=false
NEW_EXECUTION_AUTHORIZED=false
LIVE_AUTHORIZATION_ISSUED=false
EFFECT_CLAIMS_PERMITTED=false
MODEL_REQUESTS_PERFORMED=0
GPU_EXECUTION_PERFORMED=false
KAGGLE_EXECUTION_PERFORMED=false
NETWORK_TRANSPORT_PERFORMED=false
```

The manifest freeze and the later execution authorization remain distinct controls.

## Merge-history custody

The accepted repository history must preserve the first-containing commit as an ancestor.

Therefore this tranche must be merged with a normal merge commit that preserves feature commits.
Squash merge and rebase merge are prohibited for this PR because either would rewrite the
first-containing commit identity that this custody receipt binds.

If the accepted history does not contain
`078c1da32fe7c1ee8ff5a8661e5f38e588782abc` as an ancestor, custody validation fails closed and the
repository freeze gate is not accepted.

## Manifest immutability

This tranche does not modify:

`data/evals/benchmark/freeze-v3/final_342_execution_manifest_v1.json`

Any later byte change to that manifest invalidates the custody receipt.

## Next gate

`BIND_FINAL_342_STATIC_EXECUTION_AUTHORITY_V1`

That later gate binds execution authority to the frozen manifest identity. It remains
non-equivalent to live issuance and must not perform final measured execution merely because the
manifest is frozen.
