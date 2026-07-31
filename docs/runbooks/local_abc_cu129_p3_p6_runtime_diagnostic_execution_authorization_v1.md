# Runbook: P3-P6 Runtime Diagnostic Execution Authorization V1

## Current state

`IMPLEMENTED_NOT_ISSUED`

Merging this issuer does not authorize runtime execution.

## Module

```text
auragateway.local_abc.full_abc_local_environment_qualification_cu129_p3_p6_runtime_diagnostic_execution_authorization_v1
```

## Static validation

```powershell
python -B -m $Module validate-implementation --repo-root .
```

## Transient paths

These files must remain untracked and must never be committed:

```text
benchmarks/local_abc/auragateway_cu129_p3_p6_runtime_diagnostic_execution_authorization_v1.json
benchmarks/local_abc/auragateway_cu129_p3_p6_runtime_diagnostic_execution_authorization_consumption_v1.json
```

## Future issuance

Issue only from synchronized, clean `main` after explicit operator
confirmation. The confirmation must bind:

```text
scope: P3_P6_RUNTIME_DIAGNOSTIC_V1
notebook SHA-256: bf2e02f9bfe5e663942dbcc0ada2cc62c799d7a8b81da813b3d7cb2ddca194b7
model snapshot SHA-256: 84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94
backend: TRITON_ATTN
maximum window: 240 minutes
```

## Future Kaggle settings

```text
notebook: ag-cu129-p3-p6-runtime-diagnostic-v1
failed lineage: ag-cu129-p3-p6-runtime-diag-failed-v1
accelerator: T4 x2
Internet: Off
secrets: none
inputs: exact model snapshot plus exact governed CUDA 12.9 wheelhouse
```

The governed attempt must stop after the first failed probe, preserve partial
evidence, and emit the deterministic evidence archive and complete Kaggle log.
Do not manually execute cells before `Save Version -> Save & Run All`.

## Consumption

Every saved-version attempt consumes the authority, including PASSED, FAILED,
or INTERRUPTED. Record the positive Kaggle saved-version ID. Do not rerun an
unchanged failed notebook; rename it first.

## Enforcement limitation

The notebook does not parse the transient authorization artifact. Runtime-loader
authorization enforcement is not claimed. The authority is an operator gate
bound to exact Git, notebook, model, wheelhouse, time-window, and action-budget
identities.
