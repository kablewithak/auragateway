# Runbook: Exact-Runtime P5/P6 Requalification V2 Authorization Issuer

## Static implementation phase

This PR may generate and validate only the issuer review and implementation record.
It must not create a live authorization, terminal receipt, control materializer,
or Kaggle execution.

```powershell
python -m auragateway.local_abc.p5_p6_exact_runtime_execution_authorization_v2 `
    generate `
    --repo-root .

python -m auragateway.local_abc.p5_p6_exact_runtime_execution_authorization_v2 `
    validate-implementation `
    --repo-root .
```

## Post-merge issuance boundary

Only after the issuer PR is merged and `main` is synchronized:

1. validate the merged issuer and V2 implementation;
2. record the exact issuer merge commit;
3. freshly observe Kaggle T4 x2 settings with Internet Off;
4. supply the exact operator confirmation personally;
5. create canonical compact confirmation JSON outside the repository;
6. issue once;
7. generate the CPU-only authorization control materializer from the resulting
   local authorization;
8. save its Kaggle output and attach that saved producer output to the V2 GPU
   notebook.

The exact confirmation phrase is intentionally not satisfied by this runbook or
static implementation. The operator must supply it personally at issuance time.

Validate confirmation:

```powershell
python -m auragateway.local_abc.p5_p6_exact_runtime_execution_authorization_v2 `
    validate-confirmation `
    --confirmation-json <path>
```

Issue once:

```powershell
python -m auragateway.local_abc.p5_p6_exact_runtime_execution_authorization_v2 `
    issue `
    --repo-root . `
    --confirmation-json <path>
```

The issuer performs current transport round-trip parity before writing the live
V2 authorization.

Then generate the materializer using the already-merged transport module:

```powershell
python -m auragateway.local_abc.p5_p6_exact_runtime_authorization_transport_v1 `
    generate-control-materializer `
    --authorization-path `
    benchmarks\local_abc\auragateway_p5_p6_exact_runtime_requalification_v2_execution_authorization.json `
    --output "$HOME\Downloads\ag-p5-p6-auth-control-v1.ipynb"
```

## Hard boundaries

- never reuse V1 authority;
- never overwrite live V2 authority;
- never overwrite a terminal receipt;
- never bypass the governed control materializer;
- never substitute global authorization filename `rglob`;
- no hidden retry or replacement worker;
- no pilot or final measured A/B/C authority.

## Static terminal state

```text
authorization_issuer_implemented=true
live_authorization_issued=false
runtime_execution_authorized=false
p5_p6_exact_runtime_requalified=false
pilot_execution_authorized=false
final_measured_abc_execution_authorized=false
```
