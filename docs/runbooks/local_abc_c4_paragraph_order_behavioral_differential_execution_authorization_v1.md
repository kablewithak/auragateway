# C4 Paragraph-Order Behavioral Differential Execution Authorization V1 Runbook

## Purpose

Operate the transaction-bound single-use issuer for the frozen C4 paragraph-order
behavioral differential. Static implementation and validation never authorize or run
the experiment.

## Static implementation gate

From the repository root, use the project virtual environment to generate and validate
the static issuer artifacts:

```text
python -m auragateway.local_abc.c4_paragraph_order_behavioral_differential_execution_authorization_v1 generate --repo-root .
python -m auragateway.local_abc.c4_paragraph_order_behavioral_differential_execution_authorization_v1 validate --repo-root .
```

Expected static state:

- `IMPLEMENTED_NOT_ISSUED`
- live authorization absent
- live manifest absent
- platform-observation receipt absent
- terminal receipt absent
- model requests = 0
- Kaggle execution = false

Do not run `authorize-generate` before the issuer implementation is merged and local
`main` is synchronized to `origin/main`.

## Fresh issuance gate

Live issuance requires:

- clean synchronized `main`;
- merged authorization design;
- merged issuer implementation;
- exact bound artifact identities;
- fresh dynamic SHA-256 challenge;
- manual exact retype within 15 minutes.

The issuer prints the exact authority scope, hashes, budget, CTTCCT request order, and
required platform before requesting the retype.

The generated notebook defaults to:

`Desktop/ag-c4-paragraph-order-behavioral-differential-v1.ipynb`

Issuance creates one live authorization and one live manifest. It does not run Kaggle.

## Platform observation gate

After the transaction-bound notebook exists, but before Save & Run All:

1. open Kaggle notebook settings;
2. confirm accelerator is T4 x2 / two allocated GPUs;
3. confirm Internet is Off;
4. record the observation timestamp;
5. persist the durable receipt with `record-platform-observation`.

The receipt is bound to the transaction and manifest and is not mounted as runtime
input.

No Save & Run All is authorized until this receipt exists.

## Execution gate

Only one Save & Run All is allowed.

The bound runtime budget is:

- 6 requests;
- 6 loads;
- 6 fresh workers;
- 6 teardowns;
- 0 hidden retries;
- 0 replacement observations;
- 0 network requests;
- R0 spend.

The runtime must preserve CTTCCT ordering and the frozen control-anchor rules.

## Terminalization

Every attempted execution consumes the authorization.

Allowed terminal dispositions:

- `CONSUMED`
- `OUTCOME_UNKNOWN`
- `EXPIRED_UNUSED`
- `CANCELLED_UNUSED`
- `ABANDONED_BEFORE_EXECUTION`

A successful (`PASSED`) terminal outcome requires the durable platform-observation
receipt. `OUTCOME_UNKNOWN` must not fabricate an execution outcome.

Terminal authority is never reusable.

## Failure precedence

The first attributable material divergence is primary. Cleanup, evidence persistence,
or reporting failures are secondary and must not overwrite the primary failure.

The generated wrapper treats `SystemExit(0)` and `SystemExit(None)` as successful bound
runtime completion rather than a primary failure.

## Evidence policy

Do not retain raw prompts, raw model outputs, credentials, customer data, or secrets.
Preserve only the governed evidence bundle and identity-bearing receipts required by
the frozen design.

## Next gate after static merge

`MERGE_THEN_ISSUE_FRESH_C4_PARAGRAPH_ORDER_BEHAVIORAL_DIFFERENTIAL_EXECUTION_AUTHORIZATION_V1`
