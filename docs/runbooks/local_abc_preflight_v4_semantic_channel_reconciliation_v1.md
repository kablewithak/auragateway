# Runbook: Preflight V4 semantic-channel reconciliation

## Purpose

Validate the repository-only reconciliation after Final Offline Verifier V4
saved version `341211001`.

This runbook performs **No Kaggle execution**.

It performs no package installation, model load, worker start, model request,
benchmark trajectory, network request, or runtime authorization issuance.

## Commands

Generate the deterministic record:

```powershell
python -m auragateway.local_abc.preflight_v3_exact_runtime_offline_compatibility_v4_semantic_channel_reconciliation_v1 generate --repo-root .
```

Validate the generated record:

```powershell
python -m auragateway.local_abc.preflight_v3_exact_runtime_offline_compatibility_v4_semantic_channel_reconciliation_v1 validate-generated --repo-root .
```

Validate the complete reconciliation package:

```powershell
python -m auragateway.local_abc.preflight_v3_exact_runtime_offline_compatibility_v4_semantic_channel_reconciliation_v1 validate-implementation --repo-root .
```

## Safety

No successor execution authorization may be created by this tranche.

The consumed V4 authority remains non-reusable.

V4 and saved version `341211001` remain immutable diagnostic evidence.

## Exit

Expected next gate:

`design_semantic_channel_safe_final_offline_verifier_v5_successor`
