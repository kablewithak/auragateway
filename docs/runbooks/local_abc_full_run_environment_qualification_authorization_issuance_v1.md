# Local A/B/C Environment Qualification Authorization Issuance v1

## CURRENT STATUS: ISSUER BLOCKED PENDING POST-INTEGRATION REBIND

The hardened CUDA 12.9 harness sourced from `4f3302df871d47fec81e25e9af9609c0e2c7812d` has been
published, CPU-materialized, metadata-inspected, and integrated as the current
operational input.

```text
source_commit=4f3302df871d47fec81e25e9af9609c0e2c7812d
harness_directory_sha256=a154f3453c55571fc7535b546e4a97a66756ceb1900b51c2fd1336fed981d307
harness_file_count=1095
harness_total_bytes=11034996
operational_input_closure=PASSED
authorization_issued=false
gpu_execution_performed=false
model_requests_performed=0
```

The immutable vLLM CLI failure and hardening record remain preserved. The
corrected harness uses `--no-enable-log-requests` and retains the installed
`api_server --help` capability gate before worker spawn.

The issuer is implemented but remains fail-closed on this integration branch.
Its authorization base commit must be rebound to the eventual integration merge
commit before operator-confirmed issuance.

```text
fresh_issuer_implemented=true
fresh_issuer_usable=false
historical_issuer_usable=false
active_harness_reusable_for_retry=true
authorization_issued=false
next_gate=post_merge_fresh_cu129_authorization_rebind
```

The frozen authorization payload compatibility policy remains:

```text
CONTROL_PACKAGE_AUTHORIZATION_PARITY
```

## Current harness authority

```text
source commit:
4f3302df871d47fec81e25e9af9609c0e2c7812d

mounted path:
/kaggle/input/notebooks/kabomolefe/ag-harness-materializer-cu129-v1/ag_harness_materializer_cu129_v1_output/auragateway_qualification_harness_4f3302d_v1

directory SHA-256:
a154f3453c55571fc7535b546e4a97a66756ceb1900b51c2fd1336fed981d307

materializer saved version:
338367572

inspection saved version:
338369540

inspection evidence ZIP SHA-256:
2574307d69c9cf8ab0316bdf5be13cbfdfa5ced0febde9d4da0d87bc7ddb3f34
```

## Validate the blocked issuer boundary

```powershell
python -m auragateway.local_abc.full_abc_local_environment_qualification_execution_authorization_issuance `
    validate-implementation `
    --repo-root .
```

Required status:

```text
FRESH_CU129_AUTHORIZATION_ISSUER_BLOCKED_PENDING_POST_INTEGRATION_REBIND
```

## Validate the authority graph

```powershell
python -m auragateway.local_abc.full_abc_local_environment_qualification_cu129_authority_graph `
    --repo-root .
```

Required output includes:

```text
status=CURRENT_CU129_HARDENED_HARNESS_INTEGRATED_PENDING_AUTHORIZATION_REBIND
operational_input_closure=PASSED
fresh_cu129_authorization_issuer_usable=false
active_harness_reusable_for_retry=true
authorization_issued=false
runtime_execution_performed=false
model_requests_performed=0
next_gate=post_merge_fresh_cu129_authorization_rebind
```

## Hard limits retained

```text
maximum authorization window: 240 minutes
maximum Kaggle sessions: 1
maximum workers: 2
maximum model requests: 8
maximum output tokens per request: 32
benchmark trajectory requests permitted: 0
network access permitted: false
credentials permitted: false
customer data permitted: false
external spend: 0
measured execution authorized: false
```

## Required post-merge sequence

1. merge this evidence-integration branch;
2. synchronize clean `main`;
3. bind the issuer to the exact integration merge commit;
4. validate manifest, materialization, launcher, runtime adapter, diagnostics,
   and frozen authorization-loader parity;
5. obtain explicit operator confirmation;
6. issue one fresh transient authorization without overwriting;
7. generate and run one CPU-only control materializer;
8. permit at most one governed fresh-session T4 x2 qualification attempt.

## Prohibited actions

- do not issue authorization from this integration branch;
- do not commit a transient authorization;
- do not rewrite historical evidence or the 56f3373 integration records;
- do not overwrite an existing authorization;
- do not start Kaggle or enable a GPU from this branch;
- do not install packages, load a model, start workers, or perform requests;
- do not authorize measured A/B/C;
- do not claim environment qualification, measured improvement, or production
  readiness.

## Next gate

```text
post_merge_fresh_cu129_authorization_rebind
```
