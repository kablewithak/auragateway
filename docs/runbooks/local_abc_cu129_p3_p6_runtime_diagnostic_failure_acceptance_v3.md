# Runbook: P3-P6 Runtime Diagnostic Failure Acceptance V3

## Generate

```powershell
$Module = (
    'auragateway.local_abc.' +
    'p3_p6_runtime_diagnostic_failure_acceptance_v3'
)

python -B -m $Module generate --repo-root (Get-Location).Path
if ($LASTEXITCODE -ne 0) {
    throw 'V3 failure-acceptance generation failed.'
}
```

## Validate

```powershell
$Module = (
    'auragateway.local_abc.' +
    'p3_p6_runtime_diagnostic_failure_acceptance_v3'
)

python -B -m $Module validate --repo-root (Get-Location).Path
if ($LASTEXITCODE -ne 0) {
    throw 'V3 failure-acceptance validation failed.'
}
```

## Required terminal interpretation

- lifecycle outcome: `FAILED`;
- evidence disposition: `QUARANTINED_INVALID_DIAGNOSTIC`;
- authorization reusable: `false`;
- unchanged replay authorized: `false`;
- formal P3 acceptance established: `false`;
- next gate:
  `design_and_merge_p3_p6_runtime_evidence_contract_hardening_v4`.

Do not issue new runtime authorization in this tranche.
