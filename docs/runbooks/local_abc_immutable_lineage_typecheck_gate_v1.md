# Immutable-Lineage Typecheck Gate V1 Runbook

## Validate the policy

```powershell
python -m auragateway.local_abc.immutable_lineage_typecheck_gate `
    validate-policy `
    --repo-root $RepoRoot
```

Expected status:

```text
IMMUTABLE_LINEAGE_TYPECHECK_POLICY_VALID
```

## Run the gate

```powershell
python -m auragateway.local_abc.immutable_lineage_typecheck_gate `
    run `
    --repo-root $RepoRoot
```

Expected status:

```text
PASSED_WITH_EXACT_IMMUTABLE_LINEAGE_EXCEPTION
```

The gate passes only when mypy reports the one exact reviewed diagnostic and no others. Raw `python -m mypy` continues to exit with code `1`; repository workflows should call this gate when evaluating typecheck regression safety.

## Failure handling

Do not update the policy automatically. Preserve the complete error envelope and classify the divergence:

- immutable source or pyproject identity drift;
- mypy version drift;
- missing reviewed diagnostic;
- unexpected new diagnostic;
- command timeout or stderr output.

Any accepted-source change requires an explicit lineage migration rather than a policy refresh.

## Safety

The gate performs no network calls, provider calls, GPU work, model loading, runtime authorization, or external spend.
