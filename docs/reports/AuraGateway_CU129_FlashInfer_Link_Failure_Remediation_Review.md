# AuraGateway CUDA 12.9 FlashInfer Link Failure Remediation Review

## Outcome

The failed governed qualification is classified as:

```text
FLASHINFER_JIT_CUDA_DRIVER_LINK_LIBRARY_UNAVAILABLE
```

Confidence is confirmed from the bounded two-worker startup diagnostic.

## Proven execution boundary

- the fresh four-file control package materialized successfully;
- the exact governed launcher executed;
- the isolated CUDA 12.9 runtime installed;
- vLLM 0.19.1 entered both worker processes;
- the Qwen snapshot weights loaded;
- automatic attention selection chose FlashInfer;
- FlashInfer JIT compilation reached shared-object linking;
- both workers failed because `/usr/bin/ld` could not resolve `-lcuda`;
- neither worker reached health readiness;
- zero model requests and zero benchmark trajectories were performed.

## Approved implementation boundary

The next implementation must freeze `TRITON_ATTN` through the pinned vLLM
API-server CLI, validate that option before worker spawn, capture the selected
backend in the dependency lock, regenerate both command hashes, and regenerate
the transitive qualification assets.

## Rejected approaches

- unchanged rerun;
- silent backend fallback;
- Kaggle-specific `libcuda.so` symlink or loader shim;
- precompiled FlashInfer kernels for this bounded v1;
- model or wheelhouse replacement without separate evidence.

## Authority state

The current harness remains immutable historical evidence and is not reusable
for a retry. The consumed authorization remains archived, non-restorable, and
non-reusable.

## Non-claims

No Triton execution, healthy worker pair, inference, cache qualification,
measured A/B/C execution, performance improvement, or production readiness is
claimed.
