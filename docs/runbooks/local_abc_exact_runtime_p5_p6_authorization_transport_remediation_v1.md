# Runbook: Exact-Runtime P5/P6 Authorization Transport Remediation V1

## Purpose

Validate the repository-only V2 authorization transport remediation.

This runbook does not issue authorization and does not execute Kaggle.

## Static generation

Generate the deterministic V2 review, implementation record, and notebook:

```powershell
python -m auragateway.local_abc.p5_p6_exact_runtime_requalification_v2 `
    generate `
    --repo-root .
```

Validate generated assets:

```powershell
python -m auragateway.local_abc.p5_p6_exact_runtime_requalification_v2 `
    validate-generated `
    --repo-root .
```

Validate the generated notebook:

```powershell
python -m auragateway.local_abc.p5_p6_exact_runtime_requalification_v2 `
    validate-notebook `
    --repo-root .
```

Validate the complete remediation implementation:

```powershell
python -m auragateway.local_abc.p5_p6_exact_runtime_requalification_v2 `
    validate `
    --repo-root .
```

## Future control-materializer generation

This command is intentionally unusable until a later merged V2 authorization
issuer creates one fresh live authorization:

```powershell
python -m auragateway.local_abc.p5_p6_exact_runtime_authorization_transport_v1 `
    generate-control-materializer `
    --authorization-path `
    benchmarks\local_abc\auragateway_p5_p6_exact_runtime_requalification_v2_execution_authorization.json `
    --output `
    "$HOME\Downloads\ag-p5-p6-auth-control-v1.ipynb"
```

The generated notebook must be imported to Kaggle as:

```text
name: ag-p5-p6-auth-control-v1
Accelerator: None
Internet: Off
Secrets: None
```

Use only `Save Version -> Save & Run All`.

Its saved output must contain exactly:

```text
ag_p5_p6_auth_control_v1/
    control_package_manifest.json
    execution_authorization_v1.json
    materialization_receipt.json
```

A future V2 governed GPU notebook attaches the saved control-materializer output
alongside the already accepted wheelhouse and model resources.

## Prohibited shortcuts

Do not:

- edit or regenerate the executed V1 notebook;
- restore direct authorization-dataset transport;
- replace the V1 shallow glob with global authorization `rglob`;
- add wrapper-directory tolerance;
- weaken exact file cardinality;
- reuse the consumed V1 authorization;
- issue a V2 authorization before the V2 issuer is separately designed and
  merged.

## Expected repository state

```text
p5_p6_exact_runtime_requalified=false
runtime_execution_authorized=false
pilot_execution_authorized=false
final_measured_abc_execution_authorized=false
fresh_authorization_issuer_implemented=false
fresh_authorization_issued=false
```

## Exit gate

`DESIGN_AND_MERGE_EXACT_RUNTIME_P5_P6_REQUALIFICATION_V2_EXECUTION_AUTHORIZATION_ISSUER`
