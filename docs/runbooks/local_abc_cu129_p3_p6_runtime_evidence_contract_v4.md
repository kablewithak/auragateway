# Runbook: P3-P6 Runtime Evidence Contract V4

## Repository implementation

Generate:

```powershell
python -B -m auragateway.local_abc.full_abc_local_environment_qualification_cu129_p3_p6_runtime_diagnostic_v4 generate --repo-root .
```

Validate:

```powershell
python -B -m auragateway.local_abc.full_abc_local_environment_qualification_cu129_p3_p6_runtime_diagnostic_v4 validate --repo-root .
```

Run focused tests:

```powershell
python -m pytest -q tests/unit/local_abc/test_full_abc_local_environment_qualification_cu129_p3_p6_runtime_diagnostic_v4.py
```

## Runtime boundary

This implementation does not authorize Kaggle execution.

After merge, implement and merge a separate V4 single-use authorization bound
to:

- synchronized main;
- exact V4 notebook SHA-256;
- exact runtime-script SHA-256;
- exact request, review, source, template and implementation-record identities;
- the existing offline wheelhouse and model snapshot;
- one T4 x2 session with Internet disabled;
- the existing hard action budget.

## Failure handling

A future attempt must stop on first failure, consume authorization as `PASSED`,
`FAILED` or `INTERRUPTED`, preserve partial evidence and prohibit unchanged
replay.

Raw worker logs remain outside the evidence ZIP. Source and authored documents
receive formatting checks; immutable captured evidence receives byte-identity
checks.
