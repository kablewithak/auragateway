# ADR: Preflight-v3 exact-runtime materialization V1

Date: 2026-08-08

## Status

Proposed for merge.

## Context

Runtime-lineage reconciliation is closed on main `5e5f64a47db9665e7044748d93a554aa9f55b606`.

The final preflight-v3 experiment is planned around Python 3.12, CUDA 12.9,
vLLM `0.25.1+cu129`, wheel SHA
`9e206f370c934a2d4b6b1f05d3d09708d344e05d80260189ef19f60755709431`,
and torch `2.11.0+cu129`.

The repository already has mature CUDA 12.9 wheelhouse machinery, but that
machinery is hard-bound to vLLM `0.19.1`, torch `2.10.0+cu129`, and a
176-artifact exact resolution lock.

## Decision

`EXTEND_EXISTING_CU129_MATERIALIZER_WITH_NEW_EXACT_RUNTIME_LOCK`

This is not a from-scratch implementation and it is not safe direct reuse.

Reuse the mechanism for CPU-only dependency reconnaissance, exact artifact
hash locking, explicit host policy, isolated materialization, fresh offline
verification, pip check, native-import gates, and zero-model-request evidence.

The new preflight-v3 line must independently freeze:

- exact vLLM 0.25.1+cu129 artifact identity;
- exact SHA matching preflight-v3;
- torch 2.11.0+cu129 dependency closure;
- exact artifact set and host policy;
- new resolution lock;
- new materializer/verifier identities;
- new typed validation record.

The existing 0.19.1 resolution lock must remain historical authority and may
not be edited into the new line.

## First external gate

Before materialization or GPU work, run a CPU-only resolution reconnaissance:

```text
Accelerator=None
Internet=On
package_installation=false
model_loads=0
model_requests=0
benchmark_trajectories=0
customer_data=false
credentials=false
external_spend=0
```

The reconnaissance resolves package metadata and exact artifacts but does not
produce an accepted wheelhouse.

## Acceptance

A new resolution lock may be frozen only if the planned vLLM artifact resolves
to the exact preflight-v3 SHA, torch 2.11.0+cu129 resolves, every artifact has
a digest, every host is explicit, and no installation/model execution occurs.

## Authorization

```text
runtime_execution_authorized=false
pilot_execution_authorized=false
final_measured_abc_execution_authorized=false
```

## Next gate

`implement_preflight_v3_exact_runtime_resolution_reconnaissance_v1`
