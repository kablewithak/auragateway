# Runbook: P4 Output-Contract Diagnostic V2

## Repository validation

```powershell
python -m auragateway.local_abc.p4_output_contract_diagnostic_v2 generate --repo-root $RepoRoot
python -m auragateway.local_abc.p4_output_contract_diagnostic_v2 validate-package --repo-root $RepoRoot
pytest -q tests/unit/local_abc/test_p4_output_contract_diagnostic_v2.py
```

## Execution boundary

V2 does not issue its own execution authorization. After merge, create a separate authorization bound to the exact V2 notebook and runtime hashes.

Kaggle execution must use T4 x2, Internet Off, the exact governed wheelhouse, and the exact governed model snapshot. No unchanged V1 replay is allowed.

## Expected pre-execution state

```text
runtime_execution_authorized=false
measured_abc_execution_authorized=false
inspection_saved_version=340657269
inspection_classification=NATIVE_LIBRARY_SEARCH_PATH_SUPPORTED
next_gate=merge_then_design_separate_p4_output_contract_execution_authorization_v3
```

## Rollback

Before commit, remove only the V2 candidate paths and the copied inspection evidence. Never edit V1 evidence or notebook bytes. After commit, use an ordinary Git revert.
