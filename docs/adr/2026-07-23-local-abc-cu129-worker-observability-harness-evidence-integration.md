# ADR: Integrate the worker-observability CUDA 12.9 harness evidence

**Date:** 2026-07-23
**Status:** Accepted

## Decision

Promote the post-PR #138 worker-observability harness as the active CUDA 12.9 qualification input only after successful CPU-only materialization and independent metadata-only downstream inspection.

The accepted authority is:

- source commit: `dceda98989386de7a4d57616f9f8a8023f866f10`
- mounted path: `/kaggle/input/notebooks/kabomolefe/ag-worker-obs-harness-materializer-v1/ag_worker_obs_harness_materializer_v1_output/auragateway_qualification_harness_dceda98_worker_obs_v1`
- directory SHA-256: `c66f2589bdf55ab34f82bffc1eaaa4b4c7e73cb8195867333ccd99a58438f3e4`
- file count: `1076`
- total bytes: `10850278`
- materializer saved version: `337284215`
- inspection saved version: `337286728`
- inspection evidence ZIP SHA-256: `e1bf87f44c3ccbf3eda65938cb61b833c95edfb7c200e5f40095eab9e3f936fb`

The active binding status is `WORKER_OBSERVABILITY_HARNESS_EVIDENCE_INTEGRATED`.

## Why

The historical `426f57d` harness cannot represent the executable worker-startup diagnostics merged by PR #138. Reusing or relabeling it would break source-to-harness identity and make a later GPU result non-auditable.

The new materializer proved exact recovery from Kaggle's expanded input representation. The separate inspection notebook then proved that the saved notebook output mounts under the exact downstream consumer contract with the expected runtime adapter, worker-startup diagnostics, launcher lineage, runtime wheelhouse authority, model snapshot authority, and no transient authorization.

## Authority transition

This integration:

- migrates the active offline dataset manifest and materialization record;
- regenerates the governed launcher against the new mounted path;
- preserves `CONTROL_PACKAGE_AUTHORIZATION_PARITY`;
- retires the historical harness only as the active binding, not as evidence;
- records fresh authorization readiness;
- leaves the historical authorization issuer unusable;
- does not issue authorization.

## Safety

```text
authorization_issued=false
gpu_execution_performed=false
package_installation_performed=false
model_loaded=false
worker_started=false
model_requests_performed=0
measured_execution_authorized=false
```

## Next gate

`fresh_cu129_authorization_issuance_implementation`

A later PR must bind a new short-lived authorization to the post-integration merge commit and the exact current manifest, materialization, runtime-adapter, diagnostics, and launcher identities. No GPU session may start before that authority exists.
