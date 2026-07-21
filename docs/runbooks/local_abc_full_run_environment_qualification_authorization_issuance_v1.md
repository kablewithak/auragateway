# Local A/B/C Environment Qualification Authorization Issuance v1

## CURRENT STATUS: ISSUANCE BLOCKED

The historical PR #109 authorization-issuance review does **not** authorize the
current CUDA 12.9 wheelhouse runtime.

The repository now binds:

```text
runtime role: vllm_runtime
artifact format: python_wheelhouse_directory
runtime output directory: auragateway_vllm_cu129_wheelhouse_v1
package count: 176
installation executor: BASE_PIP_TARGET_DIRECTORY
Python startup: NO_SITE_WITH_CONTROLLED_SITE_BOOTSTRAP
loader policy: TARGET_NVIDIA_LIBRARIES_PREPENDED
vLLM: 0.19.1
Torch: 2.10.0+cu129
Transformers: 5.5.3
```

PR #109 reviewed the retired single-wheel runtime. It remains historical evidence and
must be validated at its original source commit. It must not be interpreted as current
operational authority.

Attempting to issue a qualification authorization before a fresh CUDA 12.9 review must
fail with:

```text
FRESH_CU129_AUTHORIZATION_REVIEW_REQUIRED
```

## Purpose

Preserve the issuance procedure and hard safety limits while explicitly blocking final
authorization until a fresh review binds the merged CUDA 12.9 authority graph.

This runbook does not:

- issue authorization;
- start Kaggle;
- install the wheelhouse;
- load a model or tokenizer;
- start workers;
- perform model requests;
- generate runtime evidence;
- authorize measured A/B/C execution.

## Historical authority

The historical issuance-review boundary remains:

```text
PR #109 source commit:
58e448228abcf9b83e1a6d165094bbec61dcf02c

Historical authorization contract source:
211a10757999b1b110cb1d9df172938cf6ed7969

Historical harness source:
4dfd799590195d842f2382bb882fba9b8c4e2422
```

Those identities are retained for audit and provenance. Historical files are loaded
from their revision rather than validated through current live runtime enums.

## Current repository boundary

The current repository may validate all non-operational inputs, but it may not create a
final authorization. The expected state is:

```text
CUDA 12.9 integration: repository-only
final authorization: absent
Kaggle session: not started
runtime installation: not performed
model loaded: false
workers started: false
model requests: 0
measured execution authorized: false
external spend: 0
```

## Validate the current authority graph

Run from the repository root:

```powershell
python -m auragateway.local_abc.full_abc_local_environment_qualification_cu129_authority_graph `
    --repo-root .
```

Required output includes:

```text
status=CURRENT_AUTHORITY_GRAPH_VALID_HISTORICAL_AUTHORITIES_REVISION_BOUND
current_runtime_role=vllm_runtime
current_runtime_format=python_wheelhouse_directory
runtime_package_count=176
fresh_cu129_authorization_review_required=true
authorization_issued=false
runtime_execution_performed=false
model_requests_performed=0
```

## Validate current issuance inputs

This validates the materialization record, portable manifest, exact wheelhouse
authority, harness ancestry, and adapter safety without issuing authorization:

```powershell
python -m auragateway.local_abc.full_abc_local_environment_qualification_execution_authorization `
    inspect-issuance-inputs `
    --repo-root . `
    --materialization-record `
        data/evals/benchmark/environment-qualification-v1/offline_dataset_materialization_record.json `
    --runtime-manifest `
        data/evals/benchmark/environment-qualification-v1/offline_dataset_manifest.json
```

A successful inspection proves input consistency only. It does not grant execution
authority.

## Prohibited issuance command

Do not run the historical issuance command against the CUDA 12.9 runtime:

```text
python -m ...execution_authorization_issuance issue ...
```

Until a fresh review is merged, the issuance runner must reject the current request with
`FRESH_CU129_AUTHORIZATION_REVIEW_REQUIRED`.

## Fresh-review requirements

A new issuance review must bind the merged current-state identities for:

- CUDA 12.9 runtime integration record;
- qualification execution request;
- offline dataset manifest request;
- materialization record;
- portable runtime manifest;
- runtime adapter;
- worker startup plan;
- reviewed qualification notebook;
- launcher notebook;
- current execution and authorization contracts;
- current Git blobs and canonical raw-file hashes.

The fresh review must preserve these limits:

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

## Post-review issuance gate

Only after the fresh CUDA 12.9 review merges may the operator receive a new issuance
workflow. That workflow must:

1. require synchronized clean `main`;
2. bind the merge commit containing the runtime integration and authority migration;
3. verify exact current Git blobs and canonical file hashes;
4. require explicit operator confirmation;
5. create one short-lived authorization without overwrite;
6. retain zero benchmark trajectory requests;
7. preserve a rollback and expiry path.

## Fail-closed conditions

The current workflow stops if:

- the materialization projection differs from the portable manifest;
- any current JSON authority is noncanonical;
- a live runtime authority contains the retired wheel role, format, or version;
- a historical validator reads current live files instead of its original revision;
- current execution source identities drift;
- the current request is presented to the historical PR #109 issuance review;
- a final authorization artifact already exists;
- authorization, Kaggle, model, worker, request, credential, customer-data, or spend
  boundaries are crossed.

## Next gate

```text
review_fresh_qualification_authorization_and_control_output_regeneration
```

The next gate is repository review and identity regeneration. It is not Kaggle
execution.

## Non-claims

This authority migration does not prove:

- wheelhouse installation on a fresh Kaggle image;
- model or tokenizer load;
- worker health;
- cache telemetry availability;
- reset correctness;
- environment qualification;
- cache reuse;
- latency improvement;
- quality non-inferiority;
- measured benchmark authorization;
- production readiness.
