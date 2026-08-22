# Runbook: P5/P6 Mechanism-Admission Transaction-Bound Authorization Reconciliation V1

## Purpose

Validate the static reconciliation design only. This tranche does not authorize Kaggle or live authorization issuance.

## Candidate behavior

The reconciliation producer owns two generated artifacts:

- `auragateway_p5_p6_mechanism_admission_transaction_bound_authorization_reconciliation_v1.json`
- `auragateway_p5_p6_mechanism_admission_transaction_bound_authorization_reconciliation_v1_review.json`

Run `write` only to regenerate those deterministic static artifacts. Run `validate` to prove the authority split and current repository preconditions.

## Required design facts

Validation must prove:

1. PR #239 transaction-bound architecture remains byte-identical to its accepted record.
2. Mechanism-admission design and implementation-review identities remain current.
3. Existing transaction-bound P5/P6 integration still records zero authorization-specific Kaggle inputs and zero authorization producer notebooks.
4. PR #291 remains unissued and retains `GOVERNED_ROOT_EXACT_FLAT_V1` as the topology being superseded.
5. Current C4 authorization implementation still exhibits the transaction-bound dynamic-challenge and durable-observation pattern.
6. The current mechanism-admission runtime and template are present but are not modified by this tranche.

## Forbidden actions

Do not:

- issue a live authorization;
- generate a live transaction executable;
- start Kaggle;
- attach an authorization-control notebook or Dataset;
- load the model;
- start workers;
- perform model requests;
- delete or rewrite PR #291 artifacts.

## Next gate

After this design is merged and synchronized, implement a new current-scope transaction-bound issuer/runtime-admission integration. That implementation must supersede the exact-flat consumer boundary without changing P5/P6 mechanism semantics.
