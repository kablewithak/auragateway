# P5/P6 Transaction-Bound C3 Failure Reconciliation V1 Runbook

## Purpose

Validate and preserve the reconciliation of transaction
`8ad4e628eaffbfc52d46bd958588529e940881937e09ade1c5c6064a755fc9aa`.

This runbook performs repository validation only.

It does not authorize or execute Kaggle, GPUs, model loading, workers, model
requests, P5/P6 qualification, or measured A/B/C.

## Fixed evidence boundary

Primary saved version:

`341728154

Custody manifest SHA-256:

`3ca422790bdb6ff2a57c922e33f3fd7df01226d71e122f77234400a088c82103

Reconciliation record SHA-256:

`21c92d4b8adaa7157a9a4f24ff2cb9fa08c5c154224889e36d88e5e41444dbbc

Reconciliation review SHA-256:

`56b39c0085dde75640cd186d90a66168e429778681da84d7c618f6ed2fb46c56

## Required decision

The repository must preserve both truths:

1. the transaction is invalid as a single-use qualification because a duplicate
   Save Version attempt occurred;
2. the primary saved version remains useful technical diagnostic evidence.

The first technical divergence remains C3:

`model response is not valid JSON

P5 and P6 were not reached.

## Validation sequence

Run:

1. Ruff format check on the reconciliation source and tests;
2. repository Ruff lint;
3. focused mypy on the reconciliation source and tests;
4. deterministic reconciliation validation;
5. focused reconciliation pytest;
6. complete repository pytest;
7. deterministic reconciliation validation again;
8. authored-text whitespace validation;
9. exact candidate-path validation.

No generated reconciliation artifact may be manually edited.

No immutable evidence-vault artifact may be formatted or normalized.

## Post-terminal operational lifecycle closure

After the live authorization, executable manifest, and terminal receipt have
been preserved into the evidence vault and their exact byte identities have
been verified, remove only the operational lifecycle originals under
`benchmarks/local_abc`.

The preserved evidence-vault copies remain immutable.

This restores the static repository invariant required by
`transaction_bound_execution_authorization_v1.validate_static` and prevents
transient live lifecycle state from contaminating repository-wide validation.

Do not remove an operational lifecycle artifact before its preserved copy has
been identity-verified.

## Failure rule

If a deterministic identity, schema, historical authority, or evidence boundary
fails validation, stop.

Do not repair preserved historical evidence.

Do not issue new runtime authority.

Do not change the runtime merely to make the current reconciliation green.

## Next gate after merge

`DESIGN_AND_MERGE_P4_P5_COMPOSITION_DIFFERENTIAL_V1

That future tranche must remain separate from this evidence-reconciliation
transaction.
