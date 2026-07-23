# Local A/B/C Environment Qualification Authorization Issuance v1

## CURRENT STATUS: ISSUANCE BLOCKED; WORKER OBSERVABILITY HARNESS EVIDENCE INTEGRATED

The authorization issued for Attempt 5 was consumed and removed. The post-PR #138
worker-observability harness has now been materialized, independently inspected, and
integrated as the active CUDA 12.9 operational input.

The historical issuer remains deliberately stale because it binds historical source,
manifest, materialization, runtime-adapter, and launcher identities. Do not run issuer
validation, authorization issuance, authorization verification, control materialization,
or Kaggle qualification until a fresh issuer implementation is merged.

## Current active authority

```text
harness source commit:
dceda98989386de7a4d57616f9f8a8023f866f10

harness mounted path:
/kaggle/input/notebooks/kabomolefe/ag-worker-obs-harness-materializer-v1/ag_worker_obs_harness_materializer_v1_output/auragateway_qualification_harness_dceda98_worker_obs_v1

harness directory SHA-256:
c66f2589bdf55ab34f82bffc1eaaa4b4c7e73cb8195867333ccd99a58438f3e4

runtime adapter SHA-256:
f83452b6fbfd583f4236c2edbaf0e4bd3a6ece331494fdff891bf50d022ba617

worker diagnostics SHA-256:
58d39a67c9d82d1b2f5938328dfa9362ee922ced2e089f8b5d529c0139cc2b91

active launcher source SHA-256:
8d3f55d6b22ce6131de7e4cf71fa006325ecfdce3fcb0b3ed5615d32354eba59

active launcher notebook SHA-256:
4379f9ff6f82dd6bc9d63a6a7194c6805722364861f0a01f0ffd2f45263ba6d2

active manifest SHA-256:
6c998716849d20e68ded4cce3a113a791a0d863bc97d2c5027991ad6a5615d8f

active materialization record SHA-256:
a3f5cfee599b4a0258e3ac48a40f1ee27c2e9b85dd624df6fdb53079e6a6b223
```

Operational-input closure is `PASSED`. The historical `426f57d` harness and all Attempt 5
evidence remain immutable historical authorities. They are not deleted, rewritten, or
relabeled as containing worker-startup observability.

The launcher continues to preserve dynamic frozen-authorization provenance through:

```text
CONTROL_PACKAGE_AUTHORIZATION_PARITY
```

That policy does not make the historical issuer valid. The fresh issuer must bind the
post-integration merge commit rather than the earlier implementation or harness source
commit alone.

## Validate the current blocked boundary

```powershell
python -m auragateway.local_abc.cu129_worker_observability_harness_integration `
    --repo-root .
```

Required output includes:

```text
status=WORKER_OBSERVABILITY_HARNESS_EVIDENCE_INTEGRATED
operational_input_closure=PASSED
active_manifest_promoted=true
historical_issuer_usable=false
authorization_issued=false
gpu_execution_performed=false
model_requests_performed=0
next_gate=fresh_cu129_authorization_issuance_implementation
```

Also validate the complete authority graph:

```powershell
python -m auragateway.local_abc.full_abc_local_environment_qualification_cu129_authority_graph `
    --repo-root .
```

Required output includes:

```text
status=CURRENT_CU129_WORKER_OBSERVABILITY_HARNESS_EVIDENCE_INTEGRATED
fresh_authorization_base_commit_status=POST_INTEGRATION_MERGE_PENDING
fresh_cu129_authorization_readiness_review_complete=true
fresh_cu129_authorization_issuer_implemented=false
worker_startup_observability_implemented=true
historical_issuer_usable=false
active_manifest_promoted=true
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

## Post-integration sequence

After this evidence-integration PR merges:

1. synchronize clean `main` and record the exact integration merge commit;
2. implement one fresh authorization issuer bound to that merge commit;
3. bind the exact current manifest, materialization record, runtime adapter, diagnostics,
   launcher source, and launcher notebook identities;
4. preserve dynamic launcher-control authorization-source parity;
5. validate that no authorization already exists;
6. require explicit operator confirmation before issuing one short-lived authorization;
7. materialize the control package in a CPU-only fresh notebook;
8. permit at most one governed fresh-session GPU qualification retry.

## Prohibited actions

- do not reuse the Attempt 5 authorization;
- do not commit a transient authorization;
- do not update the historical issuer hashes in place;
- do not roll the active manifest back to a historical harness;
- do not run the historical `426f57d` harness as the remediated lineage;
- do not start Kaggle or GPU from the implementation branch;
- do not load a model, start workers, or perform requests during remediation proof;
- do not claim that the Attempt 5 root cause has been identified.

## Next gate

```text
fresh_cu129_authorization_issuance_implementation
```

This is a repository-only issuer implementation transition. It does not itself issue
authorization, start Kaggle, load a model, start workers, or perform requests.
