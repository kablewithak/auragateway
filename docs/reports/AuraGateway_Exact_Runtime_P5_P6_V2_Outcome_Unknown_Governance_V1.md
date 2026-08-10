# AuraGateway Exact-Runtime P5/P6 V2 Outcome-Unknown Governance V1

## Governed transaction

Kaggle saved version: `341548056`

Authorization SHA-256:

`f2ba0df653f09651bbb61904e63d2b54e6a45e74fd3910e88a82fd93b7cbb720`

Terminal receipt SHA-256:

`b2b644971de644d335f8955188f30896a0cd4354d21e92c5295dbedc13adb9ba`

Terminal log SHA-256:

`fba590846fa1a82a448f6dee96ea2bfd7a7e0b22bafcccdfb5e499fb8d6c4d0a`

Partial Kaggle results ZIP SHA-256:

`804174adc457d5cfbcd4b2df19a9fb83c5306dd014640f83bedf6313cab3c790`

## Repository disposition

`status=ACCEPTED_DIAGNOSTIC_OUTCOME_UNKNOWN`

`failure_class=HARNESS_SEMANTIC_FAILURE`

`diagnostic_masking_established=true`

`expected_governed_evidence_zip_produced=false`

`runtime_incompatibility_established=false`

`p5_failure_established=false`

`p6_failure_established=false`

`authorization_reusable=false`

## Observed execution depth

The runtime-source identity report passed with the expected V2 runtime script
identity.

The partial output contains target-runtime virtual-environment files. The
runtime-install fallback report is `NOT_RUN`, so it cannot safely be interpreted
as proof that no target-environment setup occurred.

P5 is `NOT_RUN`.

P6 is `NOT_RUN` with `current_stage=P6_NOT_STARTED`.

The run performed zero model requests.

## Terminal evidence defect

The expected governed evidence ZIP, summary, failure report, bundle manifest,
and scratch-cleanup report are absent.

The visible terminal exception occurred in `cleanup_scratch()` ->
`directory_snapshot()` and reported a symbolic link in the target runtime.

The exact earlier pre-cleanup exception, if any, is not recovered by the
preserved evidence.

## Decision

Preserve the transaction without fabricating missing evidence. Treat the V2
authorization as terminal. Do not rerun V2 unchanged and do not patch the
symbolic-link condition before the authorization architecture reconciliation.

## Next gate

`DESIGN_AND_MERGE_TRANSACTION_BOUND_EXECUTION_AUTHORIZATION_ARCHITECTURE_V1`
