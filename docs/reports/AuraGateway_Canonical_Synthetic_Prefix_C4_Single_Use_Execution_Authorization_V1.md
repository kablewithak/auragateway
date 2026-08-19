# AuraGateway Canonical Synthetic Prefix C4 — Single-Use Execution Authorization V1

## Status

`IMPLEMENTED_NOT_ISSUED`

This tranche implements the static issuer and transaction-bound wrapper required
for the previously frozen C4 authorization design. Static generation and
validation are inert.

It does not issue live authority, generate a live governed notebook, execute
Kaggle, load a model, start a worker, perform a model request, qualify C4, or
requalify P5/P6.

## Frozen Authorities

- authorization-design merge:
  `79b8ae8c1c96ea3f296725daff09615767caaefa`
- authorization-design record SHA-256:
  `191f7886be32381a54c8efb81e34c9b6434cb1f7a612d8e61e0394b7a1271463`
- C4 implementation merge:
  `9785f9f931bfa5bdd2d0bd97881759b5610eafa6`
- C4 runtime SHA-256:
  `d2cc4f38823a0133345279ed0257bf726ebcf8190ef0985620e76815700d4e82`
- qualification request SHA-256:
  `0177ad9f81aac2f4f85ab7703cedb3f17a54cab4f47c414a31691a6e21e2a884`
- reusable-prefix receipt SHA-256:
  `e6ae9dfac5653416ae02d5a8c649faa2b19a3a42529de2b1822a584335933835`
- canonical request-payload SHA-256:
  `a888c17ed8e82360fdd46d0bb6833db9db2dc3fbbfb14d861f7063b271063788`

## Static Issuer Boundary

The implementation provides five commands:

- `generate`: deterministically writes the static review and implementation record.
- `validate`: validates all static authorities and rejects any live lifecycle artifact.
- `authorize-generate`: after merge only, performs the fresh human retype ceremony
  and creates one transaction-bound notebook.
- `record-platform-observation`: records the required T4 x2 / Internet Off platform
  observation after the transaction artifact exists and before Save & Run All.
- `terminalize`: makes the authority permanently non-reusable and binds any observed
  C4 state to saved-version and evidence identities.

Only the first two commands belong to this static implementation tranche.

## Human Authorization

A later live ceremony requires a newly generated 64-character SHA-256 challenge
derived from canonical authorization-intent bytes.

The operator must manually retype the exact challenge. The assistant, issuer,
runtime, and model must not synthesize the confirmation.

The confirmation must occur within 15 minutes of intent preparation. The default
authorization window is 180 minutes and cannot exceed 240 minutes.

## Transaction Identity

The transaction ID is:

`SHA256(canonical authorization body bytes)`

The future live authorization binds:

- exact issuer merge commit;
- exact issuer source bytes;
- exact wrapper-template bytes;
- exact C4 runtime bytes;
- exact design record;
- exact implementation authorities;
- exact qualification request;
- exact reusable-prefix receipt;
- exact canonical request-payload identity;
- exact reusable-prefix token identity;
- runtime/model contract;
- C4 behavioral qualification contract;
- execution budgets;
- evidence contract;
- platform policy.

## Runtime Budget

Maximum governed actions remain:

- Kaggle sessions: `1`
- Save & Run All: `1`
- runtime install attempts: `1`
- import-closure probes: `1`
- model loads: `3`
- worker starts: `3`
- model requests: `3`
- worker teardowns: `3`
- output tokens/request: `32`
- hidden retries: `0`
- replacement requests: `0`
- external network requests: `0`
- benchmark trajectory requests: `0`
- external spend: `0`

Runtime counters remain attempt counters. Kaggle-session and Save & Run All
budgets remain platform-enforced and require later reconciliation.

## C4 Behavioral Contract

The authorization preserves the exact full prompt:

- `899` tokens;
- SHA-256
  `f009b149b0b8ccf08a423346e1736be81927095907b5221e070e59ffc6d87f4c`.

The reusable-prefix boundary remains:

- `880` tokens;
- SHA-256
  `f29af54ca46249fa63c7fd89da44ca375d64f183f8d463b3a43678318890dfb1`.

C4 requires three fresh-worker observations and exact `3/3` success. There are no
hidden retries, replacements, threshold relaxation, schema enforcement, message
restructuring, or parser relaxation.

Duplicate JSON keys are rejected. `bool` and `float` do not satisfy the required
integer `1`. `finish_reason` must be `stop`.

## Wrapper Controls

The wrapper:

1. decodes and canonicality-checks embedded authorization;
2. re-derives the transaction ID;
3. verifies runtime payload SHA-256;
4. verifies the C4 budget and qualification controls;
5. checks authorization time window;
6. checks machine-observed two-GPU topology;
7. injects the transaction ID into runtime global state;
8. executes the exact frozen C4 runtime;
9. treats `SystemExit(0)` as successful completion rather than a notebook error;
10. preserves a primary-failure projection if the bound runtime fails.

The durable platform-observation receipt is not mounted as a runtime input.

## Single-Use Lifecycle

An attempted execution terminalizes authority. A terminal authority is never
reusable.

The lifecycle supports:

- `CONSUMED`
- `OUTCOME_UNKNOWN`
- `EXPIRED_UNUSED`
- `CANCELLED_UNUSED`
- `ABANDONED_BEFORE_EXECUTION`

A `QUALIFIED` terminal observation requires a saved-version ID, durable platform
receipt identity, and evidence ZIP identity.

Runtime state is not repository acceptance. A later reconciliation still has to
verify the authorization lifecycle, saved Kaggle version, platform budget, runtime
identity, evidence custody, and terminal C4 state.

## Privacy

Raw prompts and raw model outputs remain excluded from retained evidence.
Credentials and customer data remain prohibited.

## Non-Claims

This implementation does not establish:

- live authorization;
- a Kaggle execution;
- C4 qualification;
- repository acceptance of C4;
- P5 requalification;
- P6 requalification;
- final A/B/C effects;
- a prefix-cache defect;
- historical root cause;
- production readiness.

## Next Gate

After this issuer is validated, committed, merged, and post-merge reconciled:

`MERGE_THEN_ISSUE_FRESH_CANONICAL_SYNTHETIC_PREFIX_C4_SINGLE_USE_EXECUTION_AUTHORIZATION_V1`
