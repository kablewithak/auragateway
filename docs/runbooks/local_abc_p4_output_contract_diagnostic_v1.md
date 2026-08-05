# Runbook: P4 Output-Contract Diagnostic V1

## Repository phase

1. Generate and validate the request, review, notebook, and implementation record.
2. Run focused Ruff, formatting, tests, immutable-lineage typecheck, repository Ruff, and pytest.
3. Merge the implementation candidate without issuing live execution authority.

## Runtime phase

Runtime execution is prohibited until a separate authorization issuer is implemented, merged,
and used with explicit operator confirmation.

When authorized:

1. Use Kaggle notebook name `ag-p4-output-contract-diagnostic-v1`.
2. Attach exactly one governed CUDA 12.9 wheelhouse and one exact model snapshot.
3. Select one T4 GPU and disable Internet.
4. Run one notebook version only.
5. Download `ag-p4-output-contract-evidence-v1.zip` and the terminal log.
6. Rename a failed notebook lineage to `ag-p4-output-contract-diag-failed-v1` before correction.
7. Consume the authorization with the exact saved-version ID and terminal outcome.

## Stop conditions

Stop immediately for source identity, input identity, installation, import closure, model load,
worker startup, backend realization, transport, teardown, or cleanup failure. Content-invalid or
schema-rejected requests are recorded as case evidence while the worker remains healthy.

## Privacy

No customer data, credentials, raw prompts, raw model output, or raw worker logs may enter the
evidence bundle.


## Output-contract verification

Before authorization issuance, verify that the declared output contract exactly equals the runtime
writer boundary. Both input-validation reports are required. `failure_report_v1.json` must exist
for successful and failed executions; success uses `status=NOT_APPLICABLE`.
