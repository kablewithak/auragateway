# Runbook: P3-P6 Runtime Diagnostic Failure Acceptance V2

## Preconditions

- synchronized `main` at `4bc54a1ac7f054d65e9a3bea4be8ee952535ed5c`;
- exact untracked V2 authorization and FAILED consumption receipt;
- saved version `339387641` preserved;
- exact evidence ZIP SHA-256 `36e15ed1a1424f15e43dfb1dea46abf5601e3241e2a37d4258ac95041a14a3a2`;
- exact worker stdout and stderr identities;
- no V2 replay and no V3 execution authorization.

## Validation

Run deterministic generate/validate, focused tests, project mypy, repository-wide Ruff lint, changed-file Ruff format checks, and repository-wide pytest. Quarantine the two transient lifecycle files only while running tests that require their absence, then restore and hash-verify them.

## Post-merge lifecycle

After merge, verify the committed evidence matches both transient files byte-for-byte. Only then remove the transient authorization and consumption files. Preserve the failed Kaggle lineage under `ag-cu129-p3-p6-runtime-diag-failed-v2`.

## Next gate

`design_and_merge_p3_p6_runtime_process_tree_import_closure_v3`
