# Local A/B/C Environment Qualification Authorization Issuance v1

## CURRENT STATUS: ISSUANCE BLOCKED; WORKER STARTUP OBSERVABILITY IMPLEMENTED

The authorization issued for Attempt 5 was consumed and removed. The previously valid
CUDA 12.9 issuer is now deliberately stale because the runtime adapter and governed
launcher changed to add bounded worker-startup diagnostics.

Do not run issuer validation, authorization issuance, authorization verification,
control materialization, or Kaggle qualification against this changed executable
boundary.

## Historical active authority

The active manifest and materialization record still describe the consumed historical
harness:

```text
harness source commit:
426f57dd11dddc2fb8e5a703721c2189abc7a0ff

historical runtime adapter SHA-256:
aec461dcd595bfa3af286d88832ec7ef1ca2b416adca6a548f102d9543fb8dba

historical launcher source SHA-256:
7c0f7f1d466fd68a56d6b77c6e16cf69343491710052818743327b51f1d57f16

historical launcher notebook SHA-256:
7ec60fd0a162f50961f8ff66a6e3dec3c68a15617109fdc7530b2ec380294de9

active manifest SHA-256:
f7289cee9414d03d88ceb4775198e15ff9446fd99771a58c187de0d4264ef94a

active materialization record SHA-256:
284b488dece09e6b17dcf72e4dea69bbdadd440356ce353622b100c38a02100a
```

These identities remain historical authority until a new post-merge harness is
materialized, inspected, and integrated. The `426f57d` harness must not be relabeled as
the remediated lineage.

## Implemented but unmaterialized authority

```text
worker diagnostics SHA-256:
58d39a67c9d82d1b2f5938328dfa9362ee922ced2e089f8b5d529c0139cc2b91

implemented runtime adapter SHA-256:
f83452b6fbfd583f4236c2edbaf0e4bd3a6ece331494fdff891bf50d022ba617

implemented launcher source SHA-256:
454d5e6fe7f7ff5711710d140f0bece3ee84f3a863a7c33316f784af13724bd0

implemented launcher notebook SHA-256:
8477a8f389fe21a925d87c6c4e5b7a71e9de1b1c09910d5d293eadbf6b73db26
```

The launcher continues to preserve dynamic frozen-authorization provenance through:

```text
CONTROL_PACKAGE_AUTHORIZATION_PARITY
```

That compatibility policy does not make the historical issuer valid for the new
adapter or launcher bytes.

## Validate the current blocked boundary

```powershell
python -m auragateway.local_abc.full_abc_local_environment_qualification_cu129_worker_startup_observability_implementation `
    --repo-root .
```

Required output includes:

```text
status=WORKER_STARTUP_OBSERVABILITY_IMPLEMENTED_REMATERIALIZATION_REQUIRED
historical_issuer_usable=false
active_manifest_promoted=false
authorization_issued=false
kaggle_execution_performed=false
model_requests_performed=0
next_gate=merge_then_build_post_merge_worker_observability_harness_source_package
```

Also validate the complete authority graph:

```powershell
python -m auragateway.local_abc.full_abc_local_environment_qualification_cu129_authority_graph `
    --repo-root .
```

Required output includes:

```text
status=CURRENT_CU129_WORKER_OBSERVABILITY_IMPLEMENTED_REMATERIALIZATION_REQUIRED
fresh_cu129_authorization_review_required=true
fresh_cu129_authorization_issuer_implemented=false
worker_startup_observability_implemented=true
historical_issuer_usable=false
active_manifest_promoted=false
authorization_issued=false
runtime_execution_performed=false
model_requests_performed=0
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

## Post-merge sequence

After the worker-observability implementation merges:

1. build one deterministic post-merge harness source package on clean synchronized
   `main`;
2. materialize it once on Kaggle with Accelerator None and Internet Off;
3. consume one metadata-only input inspection;
4. integrate the new harness, manifest, launcher, and adapter identities from immutable
   evidence;
5. review a new short-lived issuer boundary;
6. require explicit operator confirmation;
7. permit at most one governed GPU qualification retry.

## Prohibited actions

- do not reuse the Attempt 5 authorization;
- do not commit a transient authorization;
- do not update the historical issuer hashes in place;
- do not promote active manifest identities before metadata-only inspection;
- do not run the historical `426f57d` harness as the remediated lineage;
- do not start Kaggle or GPU from the implementation branch;
- do not load a model, start workers, or perform requests during remediation proof;
- do not claim that the Attempt 5 root cause has been identified.

## Next gate

```text
merge_then_build_post_merge_worker_observability_harness_source_package
```

This is a repository and CPU-only materialization transition. It is not authorization
issuance or GPU qualification.
