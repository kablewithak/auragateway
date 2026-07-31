# Runbook: CUDA 12.9 P3-P6 Runtime Install Diagnostics V2

## Purpose

Generate and validate the V2 notebook and repository contracts. This runbook does not authorize or perform runtime execution.

## Repository commands

From the repository virtual environment:

```text
python -B -m auragateway.local_abc.full_abc_local_environment_qualification_cu129_p3_p6_runtime_diagnostic_v2 generate --repo-root <repo-root>
python -B -m auragateway.local_abc.full_abc_local_environment_qualification_cu129_p3_p6_runtime_diagnostic_v2 validate --repo-root <repo-root>
```

## Candidate boundary

Exactly ten paths:

```text
benchmarks/local_abc/auragateway_cu129_p3_p6_runtime_diagnostic_v2_record.json
benchmarks/local_abc/auragateway_cu129_p3_p6_runtime_diagnostic_v2_review.json
data/evals/benchmark/environment-qualification-v1/p3_p6_runtime_diagnostic_v2_request.json
docs/adr/2026-08-01-local-abc-cu129-p3-p6-runtime-install-diagnostics-v2.md
docs/reports/AuraGateway_CU129_P3_P6_Runtime_Install_Diagnostics_V2.md
docs/runbooks/local_abc_cu129_p3_p6_runtime_install_diagnostics_v2.md
notebooks/auragateway_cu129_p3_p6_runtime_diagnostic_v2.ipynb
src/auragateway/local_abc/full_abc_local_environment_qualification_cu129_p3_p6_runtime_diagnostic_v2.py
src/auragateway/local_abc/templates/p3_p6_runtime_diagnostic_v2.py.tmpl
tests/unit/local_abc/test_full_abc_local_environment_qualification_cu129_p3_p6_runtime_diagnostic_v2.py
```

## Required static validation

1. deterministic generate/validate parity;
2. focused V2 tests;
3. exact project mypy command;
4. repository-wide Ruff lint;
5. changed-file Ruff formatting only;
6. repository-wide pytest;
7. exact ten-path candidate boundary;
8. staged-tree and committed-tree parity.

Do not run `ruff format .`. Historical formatting debt is outside this tranche.

## Runtime contract after later authorization

```text
Notebook: ag-cu129-p3-p6-runtime-diagnostic-v2
Failed lineage: ag-cu129-p3-p6-runtime-diag-failed-v2
Accelerator: T4 x2
Internet: Off
Secrets: none
Inputs: exact expanded model snapshot plus exact governed CUDA 12.9 wheelhouse
```

The notebook must be run only through `Save Version -> Save & Run All`. No manual cell execution. Every terminal outcome consumes the later V2 authorization.

## Expected evidence

```text
runtime_install_report_v2.json
p3_worker_startup_report_v2.json
p4_deterministic_request_report_v2.json
p5_prefix_cache_reset_report_v2.json
p6_dual_worker_isolation_report_v2.json
scratch_cleanup_report_v2.json
p3_p6_runtime_diagnostic_summary_v2.json
failure_report_v2.json
bundle_manifest_v2.json
human_report_v2.md
ag-cu129-p3-p6-runtime-evidence-v2.zip
```

The ZIP must exclude scratch directories and raw worker logs and remain at or below 2 MiB.

## Stop conditions

Stop on any authority drift, unexpected repository path, failed static gate, runtime authorization file present during implementation review, or package identity mismatch. Do not issue or execute V2 from this implementation tranche.
