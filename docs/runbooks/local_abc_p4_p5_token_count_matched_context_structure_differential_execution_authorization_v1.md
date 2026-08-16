# Local ABC Runbook — Token-Matched Differential Execution Authorization V1

## Purpose

Operate the P4/P5 token-count-matched context-structure differential authorization issuer without confusing static issuer implementation with live execution authority.

## Static State

Expected after this tranche is merged:

- issuer status: `IMPLEMENTED_NOT_ISSUED`
- authorization scope: `P4_P5_TOKEN_COUNT_MATCHED_CONTEXT_STRUCTURE_DIFFERENTIAL_V1`
- authorization architecture: `TRANSACTION_BOUND_EXECUTION_ARTIFACT`
- design merge: `76f82a4bfeb583a6839ae945f53954e7dcabcfbf`
- design record SHA-256: `6ba28cdb0f2d489c5de9171ab08edad6403d9adb058fb6b84caa61e03d1b69a4`
- runtime SHA-256: `9327d3fef6b1ba2ea8e9d380338e69e6084388b0d365019af3505e8a6a880834`
- live authorization: absent
- live manifest: absent
- platform-observation receipt: absent
- terminal receipt: absent

Static `generate-static` / `validate-static` operations must not issue authority or create a governed notebook.

## Frozen Transaction Contract

Future live authority binds:

- A/B/C each at 899 prompt tokens;
- request order `A,B,C,B,C,A,C,A,B`;
- 3 observations per condition;
- fresh worker per observation;
- 9 model requests maximum;
- 9 model loads maximum;
- 9 worker starts maximum;
- 0 hidden retries;
- 0 replacement observations;
- 32 output tokens per request;
- exact repetition penalty 1.1;
- zero external network requests and zero external spend.

A must reproduce 0/3 before B/C mechanistic interpretation is allowed. Mixed results permit no mechanistic claim.

## Future Live Issuance Boundary

Do not issue until the issuer implementation is merged and local `main` is clean and synchronized with `origin/main`.

The issuer prepares a fresh authorization intent and prints a dynamic SHA-256 challenge. The human operator must manually retype that exact challenge.

Do not synthesize, paste on behalf of the operator, or automate the confirmation.

A successful future issuance creates a transaction-bound governed notebook and live lifecycle records. The static repository runtime alone is never executable authority.

## Platform Observation Boundary

After transaction-bound artifact generation and before the one Save & Run All:

1. observe Kaggle notebook settings;
2. verify accelerator `T4_X2`;
3. verify allocated GPU count `2`;
4. verify Internet is Off;
5. persist the transaction-bound durable platform observation;
6. only then proceed to the single Save & Run All.

Console-only observation is insufficient. The receipt is not a runtime authorization input.

## Terminalization

Every attempted execution terminalizes the authorization. Do not replay unchanged authority.

Use one of:

- `CONSUMED`
- `OUTCOME_UNKNOWN`
- `EXPIRED_UNUSED`
- `CANCELLED_UNUSED`
- `ABANDONED_BEFORE_EXECUTION`

If multiple executions are observed for one transaction, governed acceptance is invalid and reconciliation is required.

## Non-Claims

This issuer implementation does not establish live human authorization, a live transaction ID, a generated live notebook, platform observation, Kaggle execution, model loading, worker startup, any A/B/C result, root cause, threshold, P5/P6 requalification, North-Star support, or production readiness.
