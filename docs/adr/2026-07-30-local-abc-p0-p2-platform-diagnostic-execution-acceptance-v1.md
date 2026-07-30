# ADR: Accept the CUDA 12.9 P0-P2 platform diagnostic V2 execution

- Status: Accepted for evidence integration
- Date: 2026-07-30
- Integration base: `1cabdacc6d98691fb734322830514d6566a98e8e`
- Kaggle saved version: `339140121`

## Context

The earlier platform diagnostic failed before Triton because default native
linker search could not resolve the mounted CUDA driver. The standalone
explicit-link probe then established the real-driver action contract.

P0-P2 diagnostic V2 integrated that contract and executed one governed,
hash-locked CUDA 12.9 target installation plus one minimal Triton vector-add
kernel.

## Evidence

```text
execution log SHA-256:
dd1455f7dfbf79b85efacd32f1518d6ebabe141d2a4ed5a50844d72778b70a4a

evidence ZIP SHA-256:
e115d2f8c6c000a7666e0482e4d3d9f69bb74599fbf4f657304d456930de3240
```

The execution reached:

```text
P0_REAL_DRIVER_PREFLIGHT_PASSED
EXPLICIT_CUDA_DRIVER_LINK_PATH_CONTRACT_PASSED
CURRENT_STACK_TRITON_PRIMITIVE_PASSED
P0_P2_PLATFORM_DIAGNOSTIC_V2_PASSED
```

## Decision

Accept saved version `339140121` as positive evidence that:

- the dual-T4 platform and real CUDA driver boundary passed;
- explicit driver linking, ELF, loader resolution and `cuInit(0)` passed;
- all 182 wheelhouse manifest entries and 176 wheels passed identity checks;
- the offline target installation succeeded;
- Torch `2.10.0+cu129` and Triton `3.6.0` loaded from the target runtime;
- one Triton vector-add kernel compiled, executed and returned exact output;
- child-local linker realization selected the real driver without global
  environment mutation or CUDA toolkit stub linking.

## Sequencing decision

Integrate this evidence in its own PR before implementing an explicit Triton
attention backend.

The next implementation must preserve a narrow boundary:

```text
backend selection and import
backend capability checks
one backend primitive
no model
no worker
no inference request
no benchmark trajectory
```

## Rejected alternatives

- replay saved version `339140121`;
- jump directly to a model or worker;
- treat one vector-add primitive as full vLLM qualification;
- globally mutate linker environment;
- replace the accepted real-driver contract with CUDA toolkit stubs.

## Next gate

`DESIGN_AND_IMPLEMENT_EXPLICIT_TRITON_ATTENTION_BACKEND_V1`

## Non-claims

This evidence does not establish vLLM import, native-extension compatibility,
attention-backend compatibility, worker startup, model inference, measured
A/B/C behavior, deployment or production readiness.
