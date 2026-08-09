# Runbook: Preflight-v3 runtime verifier reconciliation V1

## Purpose

Repository-disposition V2 saved version `341096416` and freeze the final
version-specific native capability contract before implementing another offline
verifier.

This runbook performs no Kaggle execution, issues no authorization, loads no
model, starts no worker, and sends no model request.

## Branch

Recommended feature branch:

```text
fix/local-abc-preflight-v3-verifier-reconciliation-v1
```

## Generate deterministic records

```powershell
python -m `
    auragateway.local_abc.preflight_v3_exact_runtime_offline_compatibility_v2_reconciliation_v1 `
    generate `
    --repo-root .
```

## Validate repository implementation

```powershell
python -m `
    auragateway.local_abc.preflight_v3_exact_runtime_offline_compatibility_v2_reconciliation_v1 `
    validate-implementation `
    --repo-root .
```

Required state:

```text
v2_repository_disposition=ACCEPTED_DIAGNOSTIC_FAILURE
classification=STALE_VERSION_BOUND_NATIVE_EXTENSION_PROBE
runtime_incompatibility_established=false
exact_runtime_offline_verified=false
runtime_execution_authorized=false
pilot_execution_authorized=false
final_measured_abc_execution_authorized=false
next_expensive_execution_permitted=false
```

## Verify immutable external V2 evidence

Pass the exact files downloaded from Kaggle. Browser-added filename suffixes are
allowed; identity is determined by SHA-256 and semantics, not filename.

```powershell
python -m `
    auragateway.local_abc.preflight_v3_exact_runtime_offline_compatibility_v2_reconciliation_v1 `
    verify-evidence `
    --executed-notebook '<exact path to V2 executed notebook>' `
    --execution-log '<exact path to V2 execution log>' `
    --evidence-zip '<exact path to V2 evidence ZIP>'
```

Expected identities:

```text
executed notebook:
81dade4abf79f1a5984101f9e7d0091f2fb748437b1aece0538678db633202cc

execution log:
7b4ae0b97c6caae4f6ea2f099a691ca28a9fdf7215be6f2491c74dff0c2301aa

evidence ZIP:
10ed35bb8e9f9718eb7cd7e945ed8cf8503414c8ef400e70109b46fceff4e96b
```

## Focused gates

Run repository-native Ruff, format, mypy, and pytest against the new source and
test. Then run the repository's package/authority validation and repository-wide
regression gates using the accepted mypy baseline contract.

Do not replace the baseline-aware mypy gate with a generic zero-exit assumption.

## Stop conditions

Stop if:

- any bound repository authority SHA-256 drifts;
- external V2 evidence identity drifts;
- V2 required-role semantics differ;
- source parity differs;
- `vllm_module` is no longer a successful `0.25.1` observation;
- the native failure is no longer exactly the `vllm._C` missing-module failure;
- any generated record claims runtime compatibility or execution authority.

## Next gate after merge

```text
design_and_implement_final_preflight_v3_exact_runtime_offline_verifier_from_reconciled_capability_contract
```

Implementation of V3 remains separate from execution of V3.
