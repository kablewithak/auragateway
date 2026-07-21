# AuraGateway CUDA 12.9 Qualification Runtime Integration Review

**Status:** Accepted  
**Repository base:** `daa8df9`  
**Decision:** `APPROVED_FOR_BOUNDED_CU129_QUALIFICATION_RUNTIME_INTEGRATION`

## First divergence

The isolated CUDA 12.9 runtime prerequisite is technically proven and reconciled, but the
governed qualification path still binds the rejected single-wheel runtime:

- launcher input: `vllm 0.25.1+cu129` wheel;
- adapter install: global `pip install --no-deps`;
- dependency capture: global `sys.executable`;
- workers: generic `python -m vllm...`;
- worker command hashes: historical pre-target-runtime identities.

This is a repository integration gap, not a CUDA runtime failure.

## Decision

The next implementation must be atomic across the dataset contract, control package,
launcher, adapter, dependency-lock evidence, worker plan, notebook generation, and tests.
An adapter-only patch is rejected because it would create inconsistent authorization and
artifact identities.

The accepted runtime policies are:

- `BASE_PIP_TARGET_DIRECTORY`;
- `CONTROLLED_TARGET_METADATA_AND_PACKAGING`;
- `NO_SITE_WITH_CONTROLLED_SITE_BOOTSTRAP`;
- `TARGET_NVIDIA_LIBRARIES_PREPENDED`;
- exact 176-package CUDA 12.9 wheelhouse;
- vLLM `0.19.1`;
- Torch `2.10.0+cu129`;
- Transformers `5.5.3`.

## Required regressions

The implementation must reject:

- the historical `vllm_wheel` / `python_wheel` dataset role;
- global installation into the Kaggle base interpreter;
- generic worker interpreter commands;
- inherited CUDA loader precedence;
- a sibling or unrelated target runtime;
- runtime input identities not bound to the exact resolution lock and materialization
  evidence.

## Non-claims

This review performs no Kaggle execution, issues no authorization, loads no model,
starts no workers, performs zero model requests, uses no customer data or credentials,
and does not authorize measured A/B/C execution.
