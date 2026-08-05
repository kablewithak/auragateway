# Runbook: P4 Diagnostic Execution Authorization V1

## Repository implementation phase

1. Start from clean synchronized `main` at
   `5c1654c78ce398591043960fb28e5e1f03f3cc34`.
2. Install the five authored issuer files on a bounded feature branch.
3. Run focused Ruff remediation and formatting only on the issuer source and tests.
4. Generate the deterministic authorization review and implementation record.
5. Validate the complete implementation lineage and exact implementation hashes.
6. Run focused tests, immutable-lineage typecheck, repository Ruff, and full pytest.
7. Commit and merge exactly seven static issuer files.
8. Synchronize clean `main` and confirm that no transient authorization or consumption artifact
   exists.

## Issuance preconditions

Issue only after explicit operator confirmation of:

- scope `P4_OUTPUT_CONTRACT_DIAGNOSTIC_V1`;
- source-main merge `5c1654c78ce398591043960fb28e5e1f03f3cc34`;
- terminal-closure feature `d85cc387344164034e30fe57752e4f04f4d10cdd`;
- notebook, runtime-script, wrapper, request, implementation-record, and model-snapshot hashes;
- backend `TRITON_ATTN`;
- model-request budget `18`;
- runtime-output count `16`;
- explicit confirmation that terminal-path output-contract closure is complete;
- an authorization window no longer than 240 minutes.

The repository must be clean and synchronized on `main`. Authorization and consumption paths must
be untracked and absent. Issuance is non-overwriting.

## Execution phase

1. Verify the live authorization immediately before execution.
2. Use one T4 GPU with Internet disabled.
3. Attach exactly one governed CUDA 12.9 wheelhouse and one exact model snapshot.
4. Run exactly one saved notebook version without changing the A-F schedule.
5. Do not retry failed requests or repeat the notebook under the same authority.
6. Preserve the evidence ZIP and terminal log.
7. Record the saved-version ID and terminal outcome.
8. Consume the authorization for `PASSED`, `FAILED`, or `INTERRUPTED`.

## Stop conditions

Stop for identity or ancestry drift, dirty or unsynchronized `main`, tracked transient files,
expired authority, pre-existing consumption, input ambiguity, installation or import-closure
failure, model-load or worker-start failure, backend-marker failure, transport failure, surviving
capture threads, residual worker process, scratch-cleanup failure, request-budget excess, or an
incomplete pre-manifest or pre-archive output set.

Content-invalid and schema-rejected responses remain diagnostic case evidence while transport and
the worker remain healthy. Partial execution cannot select a case.

## Privacy and retention

No customer data, credentials, raw prompts, raw model output, or raw worker logs may be retained in
the evidence bundle. Transient lifecycle artifacts are local control records and must never be
committed.
