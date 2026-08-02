# Runbook: P3-P6 Execution Authorization V3

## Repository-only commands

```text
python -B -m auragateway.local_abc.full_abc_local_environment_qualification_cu129_p3_p6_runtime_diagnostic_execution_authorization_v3 generate --repo-root <repo-root>
python -B -m auragateway.local_abc.full_abc_local_environment_qualification_cu129_p3_p6_runtime_diagnostic_execution_authorization_v3 validate-implementation --repo-root <repo-root>
```

These commands generate and validate the issuer package only. They do not
issue runtime authority.

## Later issuance command

Run only after the issuer PR is merged and the operator explicitly
approves the exact scope and limits:

```text
python -B -m auragateway.local_abc.full_abc_local_environment_qualification_cu129_p3_p6_runtime_diagnostic_execution_authorization_v3 issue --repo-root <repo-root> --operator-confirm --window-minutes 240 --confirm-scope P3_P6_RUNTIME_DIAGNOSTIC_V3 --confirm-notebook-sha256 f62842a2fc08793b68ca1604165dfe16d8cff866452d7a6ab5e4c2a2b84328de --confirm-model-snapshot-sha256 84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94 --confirm-backend TRITON_ATTN
```

## Lifecycle

1. issue exactly one untracked authorization;
2. verify it immediately before execution;
3. perform exactly one Kaggle `Save Version -> Save & Run All`;
4. consume with PASSED, FAILED or INTERRUPTED and the saved-version ID;
5. preserve both transient files with runtime evidence;
6. do not replay the unchanged notebook.

## Execution settings

```text
Notebook: ag-cu129-p3-p6-runtime-diagnostic-v3
Failed lineage: ag-cu129-p3-p6-runtime-diag-failed-v3
Accelerator: T4 x2
Internet: Off
Secrets: none
Inputs: exact expanded model snapshot and governed CUDA 12.9 wheelhouse
```
