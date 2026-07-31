# Runbook: Explicit Triton attention-backend execution acceptance V1

## Purpose

Preserve and accept successful Q6 evidence from Kaggle saved version
`339181603` without replaying the notebook or issuing new runtime authority.

## Candidate boundary

The acceptance candidate contains exactly eleven repository paths:

```text
benchmarks/local_abc/
  auragateway_cu129_explicit_triton_attention_backend_execution_acceptance_v1.json

docs/adr/
  2026-07-31-local-abc-explicit-triton-attention-backend-execution-acceptance-v1.md

docs/reports/
  AuraGateway_CU129_Explicit_Triton_Attention_Backend_Execution_Acceptance_V1.md

docs/runbooks/
  local_abc_cu129_explicit_triton_attention_backend_execution_acceptance_v1.md

evidence_vault/local_abc/
  cu129-explicit-triton-attention-backend-execution-acceptance-v1/
    ag-cu129-triton-attention-backend-v1-339181603.log
    ag-cu129-triton-attention-evidence-v1-339181603.zip
    execution_authorization_v1-339181603.json
    execution_authorization_consumption_v1-339181603.json
    inspection_manifest_v1-339181603.json

src/auragateway/local_abc/
  explicit_triton_attention_backend_execution_acceptance_v1.py

tests/unit/local_abc/
  test_explicit_triton_attention_backend_execution_acceptance_v1.py
```

## Operational transient cleanup

Before generation and validation, the operational copies under
`benchmarks/local_abc/` must be absent. Preserve their exact bytes under the
evidence-vault paths first. Never commit the operational transient paths.

## Generate

```powershell
python -m auragateway.local_abc.explicit_triton_attention_backend_execution_acceptance_v1 `
    generate `
    --repo-root .
```

Required marker:

`ATTENTION_BACKEND_EXECUTION_ACCEPTANCE_V1_GENERATED`

## Validate

```powershell
python -m auragateway.local_abc.explicit_triton_attention_backend_execution_acceptance_v1 `
    validate `
    --repo-root .
```

Required marker:

`ATTENTION_BACKEND_EXECUTION_ACCEPTANCE_V1_VALIDATED`

## Hard stop

Do not rerun saved version `339181603`. Do not issue runtime authorization. Do
not start workers, load a model, issue a request, or test cache behavior in this
acceptance tranche.

## Next gate after merge

`DESIGN_AND_IMPLEMENT_P3_P6_RUNTIME_DIAGNOSTIC_V1`
