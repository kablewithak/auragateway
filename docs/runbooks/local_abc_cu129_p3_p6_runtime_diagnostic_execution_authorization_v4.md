# Runbook: P3-P6 Runtime Diagnostic Execution Authorization V4

## Repository implementation review

Run `generate`, `validate-implementation`, focused tests, project mypy,
repository Ruff, and repository pytest. Confirm the operational authorization
and consumption paths are absent and untracked.

## Live issuance prerequisites

Live issuance is a separate post-merge operation. Before issuance:

1. synchronize clean `main` with `origin/main`;
2. verify merged V4 and implementation-feature ancestry;
3. verify exact implementation, notebook, runtime-script, wrapper, model and
   wheelhouse identities;
4. confirm Internet is disabled and no credentials or customer data are
   present;
5. confirm the exact V4 scope, backend and action budget;
6. confirm no prior V4 authorization or consumption receipt exists.

## Lifecycle

Issue one transient authorization with explicit operator confirmation. Verify it
immediately before the Kaggle saved-version run. Record exactly one terminal
outcome: `PASSED`, `FAILED`, or `INTERRUPTED`. Create one non-overwriting
consumption receipt. Do not replay unchanged.

## Failure handling

Do not delete, overwrite, track, or reuse transient lifecycle artifacts after a
failed or interrupted attempt. Preserve their exact bytes with the runtime
evidence intake. Do not infer runtime success from authorization validity.
