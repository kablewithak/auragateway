# Runbook: P3-P6 Runtime Diagnostic Failure Acceptance V1

## Current state

```text
saved_version_id: 339375227
outcome: FAILED
failure_code: P3_P6_RUNTIME_INSTALL_FAILED
authorization lifecycle closed: true
authorization reusable: false
unchanged replay authorized: false
runtime execution authorized: false
root cause resolved: false
```

## Local validation

```powershell
$Module = (
    "auragateway.local_abc." +
    "p3_p6_runtime_diagnostic_failure_acceptance_v1"
)

python -B -m $Module validate --repo-root .
python -B -m pytest `
    tests/unit/local_abc/test_p3_p6_runtime_diagnostic_failure_acceptance_v1.py
python -B -m mypy --config-file pyproject.toml
python -B -m ruff check .
python -B -m pytest
```

## Retention rule

The committed evidence copies are immutable. The original transient authorization
and consumption files remain untracked until this acceptance merges and repository
copies are verified. Delete the transient originals only after merge and final
identity verification.

## Prohibited actions

- do not reuse the consumed authorization;
- do not rerun the unchanged V1 notebook;
- do not claim a pip root cause from the generic failure message;
- do not issue V2 runtime authority before V2 implementation and authorization merge.

## Next gate

`DESIGN_AND_MERGE_P3_P6_RUNTIME_INSTALL_DIAGNOSTICS_V2`
