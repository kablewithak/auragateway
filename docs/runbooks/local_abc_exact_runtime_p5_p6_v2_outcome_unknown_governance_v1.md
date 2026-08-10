# Runbook: Exact-Runtime P5/P6 V2 Outcome-Unknown Governance V1

## Purpose

Preserve and validate the terminal diagnostic evidence from Kaggle saved
version `341548056`.

This tranche performs no Kaggle execution and issues no authorization.

## Required operational lifecycle artifacts

Before preservation, the repository must contain the exact terminalized V2:

- execution authorization;
- OUTCOME_UNKNOWN terminal receipt.

The receipt must bind saved version `341548056`, the authorization SHA,
the terminal-log SHA, `execution_attempted=true`, `execution_outcome=null`,
`evidence_zip_sha256=null`, and `authorization_reusable=false`.

## Preserved external evidence

The evidence vault contains:

- the exact terminal log;
- the exact Kaggle partial-results ZIP;
- the raw partial-results ZIP; members are validated directly from the archive.

The raw partial-results ZIP must never be relabeled as the missing governed
evidence ZIP.

## Commands

Preserve lifecycle bytes idempotently:

```powershell
python -m auragateway.local_abc.p5_p6_exact_runtime_v2_outcome_unknown_governance_v1 `
    preserve-lifecycle `
    --repo-root .
```

Validate the complete governance candidate:

```powershell
python -m auragateway.local_abc.p5_p6_exact_runtime_v2_outcome_unknown_governance_v1 `
    validate `
    --repo-root .
```

## Hard boundaries

- no V2 authorization reuse;
- no unchanged V2 rerun;
- no fabricated governed evidence ZIP;
- no promotion of `MODEL_CONSTRUCTION_FAILURE` fallback labels to root cause;
- no symbolic-link remediation in this tranche;
- no model/P5/P6/runtime incompatibility claim;
- no new execution authority.

## Next gate

`DESIGN_AND_MERGE_TRANSACTION_BOUND_EXECUTION_AUTHORIZATION_ARCHITECTURE_V1`
