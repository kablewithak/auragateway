# Runbook: CUDA 12.9 P3-P6 Runtime Diagnostic V1

## Current state

`IMPLEMENTED_NOT_EXECUTED`

Runtime execution authorized:

`false`

## Repository implementation boundary

The candidate contains exactly ten paths:

```text
data/evals/benchmark/environment-qualification-v1/p3_p6_runtime_diagnostic_v1_request.json
benchmarks/local_abc/auragateway_cu129_p3_p6_runtime_diagnostic_v1_review.json
benchmarks/local_abc/auragateway_cu129_p3_p6_runtime_diagnostic_v1_record.json
src/auragateway/local_abc/full_abc_local_environment_qualification_cu129_p3_p6_runtime_diagnostic_v1.py
src/auragateway/local_abc/templates/p3_p6_runtime_diagnostic_v1.py.tmpl
notebooks/auragateway_cu129_p3_p6_runtime_diagnostic_v1.ipynb
tests/unit/local_abc/test_full_abc_local_environment_qualification_cu129_p3_p6_runtime_diagnostic_v1.py
docs/adr/2026-07-31-local-abc-cu129-p3-p6-runtime-diagnostic-v1.md
docs/reports/AuraGateway_CU129_P3_P6_Runtime_Diagnostic_V1.md
docs/runbooks/local_abc_cu129_p3_p6_runtime_diagnostic_v1.md
```

## Local validation

Use repository Python and PowerShell 5.1.

```powershell
$Module = (
    "auragateway.local_abc." +
    "full_abc_local_environment_qualification_cu129_" +
    "p3_p6_runtime_diagnostic_v1"
)

python -B -m $Module validate --repo-root .
python -B -m pytest `
    tests/unit/local_abc/test_full_abc_local_environment_qualification_cu129_p3_p6_runtime_diagnostic_v1.py
python -B -m mypy --config-file pyproject.toml
python -B -m ruff check .
python -B -m pytest
```

## Post-merge next gate

`DESIGN_AND_MERGE_P3_P6_EXECUTION_AUTHORIZATION_V1`

The authorization must bind:

- exact post-merge main commit;
- exact generated notebook SHA-256;
- exact model snapshot SHA-256;
- exact governed wheelhouse controls;
- one Kaggle session;
- T4 x2;
- Internet off;
- no secrets;
- maximum one runtime installation;
- maximum three model loads;
- maximum three worker starts;
- maximum five model requests;
- maximum 32 output tokens per request;
- zero benchmark trajectories;
- zero network requests;
- zero external spend.

The future authorization must preserve the implementation's pre-side-effect
budget guards, exact machine-readable failure taxonomy, structured JSON
response requirement, and deterministic pass/fail evidence member set.

## Future Kaggle settings

Notebook:

`ag-cu129-p3-p6-runtime-diagnostic-v1`

Failed lineage:

`ag-cu129-p3-p6-runtime-diag-failed-v1`

Accelerator:

`T4 x2`

Internet:

`Off`

Inputs:

1. exact expanded Qwen2.5-0.5B-Instruct model snapshot;
2. exact governed CUDA 12.9 wheelhouse output.

Do not attach customer data, credentials, the old Q6 authorization, or a
measured A/B/C package.

## Failure handling

Do not rerun an unchanged failed notebook. Rename the failed lineage, preserve
the complete log and evidence ZIP, consume the authorization as FAILED or
INTERRUPTED, and classify the first failed probe from
`failure_report_v1.json.error_code`.

## Non-claims

Merging the implementation does not authorize execution and does not prove
worker startup, inference, prefix reuse, reset, dual-worker isolation, A/B/C
effects, deployment, or production readiness.
