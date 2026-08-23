# AuraGateway P5/P6 Mechanism-Admission Successor 344405133 Reconciliation V1

## Governed transaction

- Kaggle saved version: `344405133`
- Transaction ID: `c657f12dbbc9e6ec4c4490f2d1c9cc492912b3a04912dd4967f7b988a7761903`
- Issuer merge commit: `7ce2e0f1312642ca9dc206c81bbf21912d07977e`
- Runtime payload SHA-256: `ecf85755c1601452a7a63be81f2d536e1106229baed0a5e58bb38e85ed4adfd4`

## Repository disposition

`status=ACCEPTED_DIAGNOSTIC_OUTCOME_UNKNOWN`

`transaction_bound_runtime_admission=PASSED`

`runtime_install_subprocess=PASSED`

`first_supported_divergence=POST_INSTALL_TARGET_RUNTIME_SNAPSHOT_SYMLINK_REJECTION`

`visible_terminal_failure=CLEANUP_SNAPSHOT_SYMLINK_REJECTION`

`diagnostic_masking_established=true`

`authorization_reusable=false`

`new_execution_authorized=false`

## Established execution depth

The transaction-bound wrapper admitted the exact governed transaction while
the authorization was live and observed two GPUs.

The retained offline-install stdout establishes successful completion of the
offline pip subprocess.

The executed runtime snapshots `TARGET_ROOT` inside `install_runtime()` before
that function returns. That snapshot rejects symbolic links. Therefore the
first supported divergence is the post-install target-runtime snapshot.

The runtime did not proceed to target-runtime validation, import-closure
validation, model construction, worker startup, model requests, P5, or P6.

Supported counters at the first divergence are therefore:

- worker starts: `0`
- model requests: `0`
- P5 executed: `false`
- P6 executed: `false`

## Diagnostic masking

The main runtime catches the first exception and begins terminal reporting.

Later, `cleanup_scratch()` calls `directory_snapshot(SCRATCH_ROOT)` before its
own protected cleanup block. The same symbolic-link invariant can therefore
raise again during cleanup and replace the externally visible traceback.

Primary and cleanup failures were not kept independently observable.

## Symlink-source disposition

The exact offending symlink member path was not preserved by saved Version
344405133 and must not be invented.

The executed runtime creates its isolated environment using `venv
--without-pip` and does not request `--copies`. The venv is therefore the
strongly established source mechanism for the incompatible symlink condition,
but the exact member pathname remains unproven.

## Supported claims

- transaction-bound execution admission worked;
- platform/authorization admission worked;
- the offline pip subprocess completed;
- the target-runtime post-install snapshot failed on a symbolic link;
- cleanup reproduced the same invariant and diagnostically masked the first
  failure;
- model construction and model requests were not reached;
- P5 and P6 were not executed or requalified.

## Non-claims

This reconciliation does not establish:

- the exact offending symlink pathname;
- P5 failure;
- P6 failure;
- downstream runtime incompatibility;
- model incompatibility;
- production readiness;
- authority for another Kaggle execution.

## Remediation boundary

The next tranche may change only the target-runtime lifecycle seam required to:

1. make isolated-environment construction compatible with the existing
   no-symlink snapshot invariant;
2. preserve the original primary failure when cleanup itself fails;
3. add regression coverage for both conditions.

P5/P6 semantics, request budgets, model identity, wheelhouse identity, and
transaction-bound authorization architecture remain frozen.

## Next gate

`IMPLEMENT_AND_MERGE_P5_P6_MECHANISM_ADMISSION_TARGET_RUNTIME_LIFECYCLE_REMEDIATION_V1`
