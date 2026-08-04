# Runbook: P3-P6 Runtime Diagnostic V5 Failure Acceptance

## Scope

This runbook validates and records the accepted failure from Kaggle saved
version `340227787`.

It does not issue runtime authorization, run Kaggle, load a model, start a
worker, or authorize measured A/B/C.

## Preconditions

- Branch is created from synchronized `main`.
- Main contains the V5 runtime implementation and V5 authorization issuer.
- The operational authorization and consumption JSON files have been copied
  into the evidence vault and removed from their transient benchmark paths.
- The worktree and index contain only this bounded candidate.
- The failed notebook is not replayed.

## Commands

Validate preserved evidence:

```powershell
python -m auragateway.local_abc.p3_p6_runtime_diagnostic_failure_acceptance_v5 `
    validate-evidence `
    --repo-root $RepoRoot
```

Generate deterministic review and record:

```powershell
python -m auragateway.local_abc.p3_p6_runtime_diagnostic_failure_acceptance_v5 `
    generate `
    --repo-root $RepoRoot
```

Validate the complete package:

```powershell
python -m auragateway.local_abc.p3_p6_runtime_diagnostic_failure_acceptance_v5 `
    validate-package `
    --repo-root $RepoRoot
```

## Required terminal state

```text
evidence_disposition=ACCEPTED_DIAGNOSTIC_FAILURE
authorization_lifecycle_closed=true
authorization_reusable=false
unchanged_replay_authorized=false
runtime_execution_authorized=false
measured_abc_authorized=false
next_gate=design_and_merge_p4_output_contract_diagnostic_v1
```

## Rollback

Before commit, remove only the exact candidate paths. Never delete the original
downloaded intake archive or the external Kaggle saved version.

After commit, use ordinary Git revert. Do not edit preserved evidence in place.

## Privacy and security

The evidence contains no customer data or credentials. Raw prompts, raw model
outputs, and raw worker-log files remain excluded. Preserve hashes, exact
saved-version identity, and authorization lifecycle receipts.
