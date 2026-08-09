# AuraGateway Preflight-v3 Final Exact-Runtime Offline Verifier V3

## Purpose

Implement the reconciled current-line offline/native capability gate for the
exact final runtime without loading a model, starting a worker, sending a
request, or executing P5/P6 or A/B/C.

## Current authority

```text
implementation base main=581a65c7856bc7530b60efcd8536f5562cd8ea15
reconciliation record SHA-256=070b625adb51e48ad29859e86d3a58c3149f17807fec9a98eafa283761c7833e
reconciliation review SHA-256=843f2c7b5d36bfcc46d50be8a1b3288dbcfb93c24cb0c4cb6d6aea11970b2d47
current boundary=P0_FINAL_RUNTIME_OFFLINE_VERIFIER_IMPLEMENTATION
```

## Exact runtime

```text
Python=3.12
Torch=2.11.0+cu129
Torch CUDA=12.9
torchaudio=2.11.0+cu129
torchvision=0.26.0+cu129
Transformers=5.14.1
Triton=3.6.0
vLLM distribution=0.25.1+cu129
vLLM module semantic=0.25.1
required CUDA native module=vllm._C_stable_libtorch
GPU topology=T4 x2
```

The input remains the accepted 196-wheel materializer output. No dependency
resolution or wheelhouse rematerialization is performed.

## Harness delta from V2

V2 proved target filesystem isolation but inherited ambient Python startup and
loader state. V3 moves all post-install target-runtime probes behind one
controlled process contract:

```text
PYTHONPATH removed
PYTHONHOME removed
LD_PRELOAD removed
PYTHONNOUSERSITE=1
target python -S
sentinel sitecustomize/usercustomize
site.main()
external site/dist-package paths removed
target NVIDIA libs first
target torch/lib before inherited system paths
real NVIDIA driver explicitly allowed
CUDA stubs/compat rejected
```

## Native proof

V3 requires three mutually reinforcing proofs:

1. filesystem inventory finds exactly one `_C_stable_libtorch*.so` in target
   vLLM;
2. `ldd` has no unresolved dependency and no prohibited package/CUDA origin;
3. `/proc/self/maps` after import confirms actual loaded origins.

Required origin policy:

```text
vLLM extension → target vllm tree
Torch/C10 native libs → target torch/lib
CUDA runtime libraries → target nvidia tree
CUDA driver → /usr/local/nvidia/lib64
system libc/loader → permitted OS runtime
external Python package native libs → prohibited
CUDA stub/compat paths → prohibited
```

This directly closes the reconciliation requirement that successful import
alone is insufficient.

## vLLM platform proof

The final capability probe invokes `CudaPlatform.import_kernels()` only after
native import and provenance pass. It verifies T4 x2 visibility and confirms the
required native module remains loaded. It performs no model construction.

## Evidence

The future saved execution writes only:

```text
input_validation.json
probe_records.json
verification_summary.json
evidence_manifest.json
```

The summary retains all attempted required roles and emits either:

```text
PASSED_PENDING_REPOSITORY_ACCEPTANCE
```

or:

```text
FAILED_PENDING_REVIEW
```

A runtime PASS from Kaggle still does not mutate repository acceptance by
itself.

## Static implementation acceptance

Before any T4 execution, repository validation must prove:

- reconciliation authority hashes unchanged;
- notebook source is unexecuted and deterministic;
- required capability roles are present;
- stale `vllm._C` import is absent;
- controlled-startup and provenance controls are present;
- model/worker/request APIs are absent;
- generated implementation review/record are canonical;
- focused and repository regression gates introduce no new debt.

## Non-claims

Implementation does not prove:

- exact runtime compatibility;
- exact-runtime P5/P6;
- cache reuse/reset;
- dual-worker isolation;
- variance-pilot readiness;
- measured A/B/C effect;
- production readiness.
