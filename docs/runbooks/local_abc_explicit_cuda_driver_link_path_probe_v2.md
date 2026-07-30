# Runbook: explicit CUDA driver link-path probe V2

## Boundary

```text
base main: f7ed2a6aec0fe47b3cde3941c476af10fb70a291
branch: feat/local-abc-explicit-cuda-driver-link-probe-v2
Kaggle execution during implementation: prohibited
```

## Local workflow

1. Apply the state-bound package.
2. Run bounded Ruff only on the two new Python files.
3. Generate the request, review, notebook and implementation record.
4. Validate deterministic regeneration and classification authority.
5. Run focused Ruff, format, project-mode mypy, focused pytest, full Ruff,
   full pytest and exact candidate checks.
6. Stage exactly nine paths.
7. Commit, push, review, merge and synchronize main.

## Generated notebook boundary

```text
name: ag-cu129-explicit-driver-link-probe-v2
accelerator: T4 x2
Internet: Off
inputs: none
sessions: 1
link attempts: 1
P2: prohibited
model, worker and request: prohibited
```

## Failure handling

A future failed notebook must be renamed:

```text
ag-cu129-explicit-driver-link-failed-v2
```

No unchanged retry is permitted. Preserve the log, summary and evidence ZIP,
then classify the first divergence.

## Tooling boundary

The repository workflow uses PowerShell, Python and Git. Pull-request creation
and Kaggle notebook execution use the browser UI. The workflow requires no
GitHub CLI and no Kaggle CLI.

## Next gate after merge

`EXECUTE_GOVERNED_EXPLICIT_CUDA_DRIVER_LINK_PATH_PROBE_V2`
