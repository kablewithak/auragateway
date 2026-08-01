# Runbook: P3-P6 Runtime Process-Tree Import Closure V3

## Scope

Generate and validate the V3 repository candidate. This runbook does not
authorize or perform runtime execution.

## Repository commands

```text
python -B -m auragateway.local_abc.full_abc_local_environment_qualification_cu129_p3_p6_runtime_diagnostic_v3 generate --repo-root <repo-root>
python -B -m auragateway.local_abc.full_abc_local_environment_qualification_cu129_p3_p6_runtime_diagnostic_v3 validate --repo-root <repo-root>
```

## Candidate boundary

Exactly ten paths: request, review, notebook, record, source, template,
tests, ADR, report and runbook.

## Required validation

1. deterministic generate/validate parity;
2. focused V3 tests;
3. exact project mypy command;
4. repository-wide Ruff lint;
5. changed-file Ruff formatting only;
6. repository-wide pytest;
7. exact ten-path candidate boundary;
8. staged-tree and committed-tree parity.

Do not run `ruff format .`.

## Runtime contract after later authorization

```text
Notebook: ag-cu129-p3-p6-runtime-diagnostic-v3
Failed lineage: ag-cu129-p3-p6-runtime-diag-failed-v3
Accelerator: T4 x2
Internet: Off
Secrets: none
Inputs: exact expanded model snapshot plus governed CUDA 12.9 wheelhouse
```

Execution must use one `Save Version -> Save & Run All`. No manual cell
execution. Every terminal outcome consumes the later V3 authorization.
