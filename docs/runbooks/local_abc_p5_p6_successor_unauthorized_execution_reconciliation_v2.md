# Runbook: P5/P6 Successor Unauthorized Execution Reconciliation V2

## Purpose

Preserve technically valid evidence from saved version `340962890` without weakening
the single-use authorization boundary.

This runbook performs no Kaggle execution and issues no authorization.

Reconciliation V1 is historical and immutable. V2 records a separate later
ungoverned execution, saved version `340962890`.

## Static commands

Generate deterministic reconciliation artifacts:

```powershell
python -m `
    auragateway.local_abc.p5_p6_successor_unauthorized_execution_reconciliation_v2 `
    generate `
    --repo-root .
```

Validate committed reconciliation artifacts:

```powershell
python -m `
    auragateway.local_abc.p5_p6_successor_unauthorized_execution_reconciliation_v2 `
    validate-implementation `
    --repo-root .
```

Verify the preserved external evidence from Downloads:

```powershell
$Downloads = Join-Path ([Environment]::GetFolderPath('UserProfile')) 'Downloads'

python -m `
    auragateway.local_abc.p5_p6_successor_unauthorized_execution_reconciliation_v2 `
    verify-evidence `
    --evidence-zip (Join-Path $Downloads 'ag-p5-p6-successor-runtime-evidence-v1.zip') `
    --terminal-log (Join-Path $Downloads 'ag-p5-p6-successor-runtime-qual-v1.log')
```

If the downloaded terminal log has a browser-added suffix, pass the exact observed
path rather than renaming evidence silently.

## Required disposition

Successful validation must retain:

```text
technical_status=PASSED
governed_acceptance_status=INVALID_UNGOVERNED_EXECUTION
authorization_lineage_status=UNESTABLISHED_AT_EXECUTION
current_line_p5_pass_accepted=false
current_line_p6_pass_accepted=false
measured_abc_eligible=false
runtime_execution_authorized=false
measured_abc_execution_authorized=false
```

## Failure handling

If external evidence identity or semantics differ, stop. Do not regenerate expected
hashes from the new bytes. Diagnose the divergence using the Semi-Formal Reasoning
certificate before changing the reconciliation authority.

## Next gate

Merge this reconciliation first. Then perform fresh capability observation and
single-use authorization issuance as a separate transaction. Issuance remains separate
from execution.
