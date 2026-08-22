# ADR: P5/P6 Mechanism-Admission Successor Execution Authorization Issuer V1

**Date:** 2026-08-22
**Status:** Accepted for implementation; no live authorization issued
**Successor merge commit:** `2b1841aee4397ae0c72bad6b2c9e7069835d8399`

## Decision

Implement one successor-specific control plane that contains both the single-use authorization issuer and the exact-flat authorization transport materializer required by the merged runtime consumer.

The tranche is implementation-only. It does not issue a live authorization, run Kaggle, load a model, start a worker, or perform a model request.

## Why a fresh issuer is required

The merged mechanism-admission successor requires scope `P5_P6_MECHANISM_ADMISSION_SUCCESSOR_V1`. Historical P5/P6 authorization issuers are bound to older scopes and older implementation identities and are not reusable authority.

The issuer may reuse proven control-plane invariants, but it must bind the current successor merge lineage, current implementation review, current design record, current mechanism-admission contract, current runtime-outcome addendum, and the generated successor runtime-script identity.

## Issuance preconditions

A future live issuance requires:

- synchronized clean `main` at the merged issuer commit;
- exact current successor artifact identities;
- fresh Kaggle T4 x2 observation;
- internet disabled;
- no credentials or customer data permitted;
- explicit operator confirmation bound to the current merged issuer commit;
- no existing live authorization;
- no prior terminal receipt for the same authorization lifecycle.

Platform observation and operator confirmation are each bounded to 15 minutes. A live authorization window may not exceed 240 minutes; the default operating window remains 180 minutes.

## Execution budget

One authorization is non-expandable and permits at most:

- one Kaggle session;
- one saved version;
- six model requests;
- three worker starts;
- three model loads;
- zero hidden retries;
- zero replacement workers;
- zero external network requests;
- zero benchmark-trajectory requests;
- zero external spend.

These ceilings match the already-merged runtime consumer contract and do not authorize variance or final A/B/C execution.

## Single-use lifecycle

The authorization begins as `ISSUED`. Any execution attempt must terminalize the authority. Unused authority may only terminalize as expired, cancelled, or abandoned. A terminal authorization is never reusable.

Known terminal dispositions are:

- `CONSUMED`
- `EXPIRED_UNUSED`
- `CANCELLED_UNUSED`
- `ABANDONED_BEFORE_EXECUTION`
- `OUTCOME_UNKNOWN`

Known execution outcomes are:

- `PASSED`
- `FAILED`
- `AMBIGUOUS`
- `INTERRUPTED`
- `DIAGNOSTIC_INVALID`

A passed execution must preserve both a saved-version identity and an evidence ZIP SHA-256.

## Transport contract

The runtime expects `GOVERNED_ROOT_EXACT_FLAT_V1` under the successor control notebook name `ag-p5-p6-mechanism-auth-control-v1` and output directory `ag_p5_p6_mechanism_auth_control_v1`.

The materialized control root contains exactly three flat files:

1. `execution_authorization_v1.json`
2. `control_package_manifest.json`
3. `materialization_receipt.json`

The materializer notebook is CPU-only, internet-off, unexecuted at generation time, and performs no model or GPU work.

## Non-claims

This tranche does not establish C4 semantic qualification, P5 requalification, P6 requalification, variance adequacy, final A/B/C results, quality non-inferiority, or production readiness.

## Next gate

After this issuer/transport tranche is merged, the next gate is a fresh platform observation followed by explicit human issuance of one successor authorization. The generated issuer record remains the formal source for the exact next-gate token.
