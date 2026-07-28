# Local A/B/C Environment Qualification Authorization Issuance v1

## CURRENT STATUS: POST-PR152 REBIND COMPLETE

The hardened CUDA 12.9 harness sourced from
`4f3302df871d47fec81e25e9af9609c0e2c7812d` has been published,
CPU-materialized, metadata-inspected, and integrated as the current operational
input. The current issuer is rebound to the merged PR #152 repository authority:

```text
current_authorization_base_commit=0805b6f08028709a347ce9e420b3415c3a84ba05
source_commit=4f3302df871d47fec81e25e9af9609c0e2c7812d
harness_directory_sha256=a154f3453c55571fc7535b546e4a97a66756ceb1900b51c2fd1336fed981d307
harness_file_count=1095
harness_total_bytes=11034996
operational_input_closure=PASSED
post_integration_rebind_complete=true
fresh_issuer_usable=true
authorization_issued=false
gpu_execution_performed=false
model_requests_performed=0
```

The immutable vLLM CLI failure and hardening record remains preserved as
historical evidence. It still records that the predecessor harness was not
retry-usable and that the issuer was blocked before rematerialization. The
current `4f3302d` harness, PR #152 integration, and rebound issuer satisfy that
historical transition without rewriting the record.

The corrected harness uses `--no-enable-log-requests` and retains the installed
`api_server --help` capability gate before worker spawn.

```text
fresh_issuer_implemented=true
fresh_issuer_usable=true
historical_issuer_usable=false
historical_vllm_cli_hardening_validated=true
active_harness_reusable_for_retry=true
authorization_issued=false
next_gate=explicit_operator_confirmation_then_issue_fresh_authorization
```

The frozen authorization payload compatibility policy remains:

```text
CONTROL_PACKAGE_AUTHORIZATION_PARITY
```

Its source-main merge identity remains the frozen
`211a10757999b1b110cb1d9df172938cf6ed7969` loader authority. It is not the
current repository authorization base and must not be rewritten.

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

## Validate the rebound issuer boundary

```powershell
python -m auragateway.local_abc.full_abc_local_environment_qualification_execution_authorization_issuance `
    validate-implementation `
    --repo-root .
```

Required status:

```text
FRESH_CU129_AUTHORIZATION_ISSUER_READY
```

Required output includes:

```text
fresh_issuer_usable=true
post_integration_rebind_complete=true
historical_vllm_cli_hardening_validated=true
authorization_issued=false
next_gate=explicit_operator_confirmation_then_issue_fresh_authorization
```

## Validate the authority graph

```powershell
python -m auragateway.local_abc.full_abc_local_environment_qualification_cu129_authority_graph `
    --repo-root .
```

Required output includes:

```text
status=CURRENT_CU129_HARDENED_HARNESS_AUTHORIZATION_REBOUND
operational_input_closure=PASSED
fresh_authorization_base_commit_status=POST_INTEGRATION_REBIND_COMPLETE
fresh_cu129_authorization_issuer_usable=true
active_harness_reusable_for_retry=true
authorization_issued=false
runtime_execution_performed=false
model_requests_performed=0
next_gate=explicit_operator_confirmation_then_issue_fresh_authorization
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

## Required sequence after this tranche merges

1. synchronize clean `main` with `origin/main`;
2. validate the rebound issuer and authority graph;
3. confirm the transient authorization path is absent and untracked;
4. obtain explicit operator confirmation;
5. issue one fresh, non-overwriting, time-bounded authorization;
6. verify the authorization against current inputs and frozen loader parity;
7. generate and run one CPU-only control materializer;
8. preserve its output as a versioned Kaggle Dataset;
9. attach that Dataset to one fresh governed T4 x2 qualification notebook;
10. permit at most one governed qualification attempt.

Authorization issuance is a separate post-merge tranche. This implementation
tranche must finish with authorization absent.

## Prohibited actions in the rebind tranche

- do not issue authorization from the feature branch;
- do not create or commit a transient authorization;
- do not rewrite historical hardening, parity, issuance-review, or consumed
  authorization evidence;
- do not change the `4f3302d` harness source, model, manifest,
  materialization, launcher, runtime adapter, diagnostics, integration, or
  readiness identities;
- do not start Kaggle or enable a GPU;
- do not install packages, load a model, start workers, or perform requests;
- do not authorize measured A/B/C;
- do not claim environment qualification, measured improvement, or production
  readiness.

## Next gate

```text
explicit_operator_confirmation_then_issue_fresh_authorization
```
