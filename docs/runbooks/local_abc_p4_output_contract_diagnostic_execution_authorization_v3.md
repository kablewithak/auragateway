# Runbook: P4 Diagnostic Execution Authorization V3

## Repository implementation phase

1. Start from clean synchronized `main` at
   `d61a146a2503a5e6bfd3fadbf1dad65dcad402ac`.
2. Create the bounded V3 authorization feature branch.
3. Add only the seven static issuer paths.
4. Format and lint only the new source and tests before generation.
5. Generate the deterministic review and implementation record.
6. Validate exact V2 artifact identities, semantic controls, and predecessor lifecycle receipts.
7. Run focused Ruff, mypy, pytest, repository Ruff, and full pytest.
8. Merge the static issuer without creating authorization or consumption artifacts.

## Issuance preconditions

Issue only from clean synchronized `main` after the V3 issuer merge. The confirmation JSON must be
canonical and must bind:

- the current issuer merge commit;
- scope `P4_OUTPUT_CONTRACT_DIAGNOSTIC_V2`;
- V2 implementation merge `d61a146a2503a5e6bfd3fadbf1dad65dcad402ac`;
- notebook, runtime-script, wrapper, request, implementation-record, and model-snapshot hashes;
- backend `TRITON_ATTN`;
- model-request budget `18`;
- runtime-output count `17`;
- one unmodified notebook and one saved version;
- no hidden retries and mandatory consumption;
- a fresh Kaggle settings observation no older than fifteen minutes;
- `GPU_T4_X2`, Internet disabled, one wheelhouse, one model snapshot, and GPU-0 worker isolation;
- an authorization window no longer than 240 minutes.

Authorization and consumption paths must be absent and untracked. Issuance is non-overwriting.

## Execution phase

1. Verify the live V3 authorization immediately before execution.
2. Upload the exact governed notebook without opening and re-saving it.
3. Use Kaggle `GPU T4 x2`, expose only GPU 0 to the worker, and keep Internet disabled.
4. Attach exactly one governed CUDA 12.9 wheelhouse and one exact model snapshot.
5. Run exactly one saved version without changing code, inputs, backend, case order, or budget.
6. Do not retry installation, imports, worker startup, requests, or the notebook under V3.
7. Preserve the terminal certificate, saved-version ID, Kaggle log, evidence ZIP, and hashes.
8. Consume V3 for every terminal outcome, including timeout or platform termination.
9. Switch off GPUs after the terminal state and preserve the saved version.

## Stop conditions

Stop for identity drift, dirty or unsynchronized `main`, tracked lifecycle artifacts, stale platform
observation, expired authority, pre-existing consumption, notebook mutation, attachment-count drift,
Internet enabled, GPU isolation drift, backend fallback, budget excess, installation or import
failure, worker exit, native-origin failure, transport failure, surviving process or capture thread,
cleanup failure, or incomplete evidence output.

A stop or failure is evidence. It does not authorize a retry.

## Privacy and retention

Do not retain customer data, credentials, raw prompts, raw model output, unrestricted environment
dumps, or raw worker logs. Keep bounded metadata-safe evidence. Lifecycle artifacts remain local and
must never be committed.
