# Runbook: P4 Output-Contract Diagnostic V1 Failure Acceptance

## Scope

This runbook preserves, validates, and records the governed failure from Kaggle saved version `340622392`.

It does not issue authorization, execute Kaggle, install a runtime, load a model, start a worker, make a request, or authorize measured A/B/C.

## Preconditions

- The branch starts from synchronized main commit `73f5962ed6852b744c3fed8e1a2e7de4fb424462`.
- The exact V1 abandonment, V2 authorization, and V2 failed consumption receipts have been copied into the evidence vault.
- The terminal log, browser intake archive, runtime evidence ZIP, and extracted reports are preserved byte-for-byte.
- The three operational transient lifecycle paths are removed only after their vault copies have been verified.
- The failed Kaggle notebook is not replayed.

## Commands

```powershell
python -m auragateway.local_abc.p4_output_contract_diagnostic_failure_acceptance_v1 `
    validate-evidence `
    --repo-root $RepoRoot

python -m auragateway.local_abc.p4_output_contract_diagnostic_failure_acceptance_v1 `
    generate `
    --repo-root $RepoRoot

python -m auragateway.local_abc.p4_output_contract_diagnostic_failure_acceptance_v1 `
    validate-package `
    --repo-root $RepoRoot
```

## Required terminal state

```text
evidence_disposition=ACCEPTED_DIAGNOSTIC_FAILURE
authorization_lifecycle_closed=true
authorization_reusable=false
unchanged_replay_authorized=false
root_cause_status=UNRESOLVED
runtime_execution_authorized=false
measured_abc_authorized=false
next_gate=design_and_merge_p4_runtime_import_closure_diagnostic_v1
```

## Rollback

Before commit, remove only the exact candidate paths. Preserve the external Kaggle saved version and original downloaded files.

After commit, use ordinary Git revert. Never edit immutable evidence in place.

## Privacy and security

The evidence contains no customer data or credentials. Raw prompts, model outputs, and unrestricted raw import output remain excluded. The next diagnostic may retain only bounded metadata-safe exception fields and hashes.
