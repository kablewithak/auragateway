# ADR: Implement a separate explicit Triton attention-backend V1 gate

- Status: Accepted for implementation
- Date: 2026-07-31
- Source main: `81597c1ebc6add70f6c35e3f2287acba9c078519`
- Runtime execution authorization: absent

## Context

PR #168 accepted the CUDA 12.9 P0-P2 platform diagnostic. The accepted evidence
closes platform identity, explicit CUDA-driver linking, offline target-runtime
installation, target Torch and Triton imports, and one generic Triton vector-add
primitive.

That evidence does not establish the vLLM attention boundary. The next unknown
is whether the governed vLLM `0.19.1` target can discover, import, attribute,
validate, compile, and execute its explicit `TRITON_ATTN` implementation on a
Tesla T4 without changing the tested backend through fallback.

The pinned vLLM registry maps:

```text
AttentionBackendEnum.TRITON_ATTN
→ vllm.v1.attention.backends.triton_attn.TritonAttentionBackend
```

The registry permits runtime overrides. A valid qualification must therefore
check both the default path and override state before importing the class.

The pinned backend declares support for:

```text
float16
bfloat16
float32
head size >= 32
block size divisible by 16
compute capability 7.5
```

Its encoder-style model-free path owns
`vllm.v1.attention.ops.triton_prefill_attention.context_attention_fwd`.

## Decision

Implement a separate, deterministic, model-free Q6 harness rather than modify
the historical worker or full-environment launcher.

The implementation contains:

```text
strict Pydantic v2 contracts
accepted PR #166 and PR #168 authority projections
deterministic request and architecture-review records
an inspectable Python program template
a deterministic two-cell Kaggle notebook
an implementation record
focused regression tests
an ADR, engineering report, and runbook
```

The future governed notebook will perform exactly one bounded sequence:

```text
dual-T4 platform preflight
→ exact wheelhouse validation
→ one offline target installation
→ exact target origin and version checks
→ explicit TRITON_ATTN registry discovery
→ override rejection
→ exact backend-class import
→ T4 decoder-configuration validation
→ exact primitive attribution
→ one model-free Triton attention primitive
→ PyTorch SDPA numerical comparison
→ immutable evidence bundle
```

The capability check uses the intended decoder-serving configuration:

```text
head_size=64
dtype=float16
kv_cache_dtype=auto
block_size=16
use_mla=false
has_sink=false
use_sparse=false
use_mm_prefix=false
use_per_head_quant_scales=false
compute_capability=7.5
attention_type=decoder
```

The primitive uses direct Q, K, and V tensors through the exact function owned
by the Triton backend. It intentionally avoids model loading, a worker process,
an inference API, KV-cache state, and request telemetry.

## Explicit fallback control

The harness fails closed when:

```text
TRITON_ATTN is overridden
the registry path differs
the imported class differs
the class name is not TRITON_ATTN
the backend module does not own the exact pinned primitive
```

Automatic backend selection is not called. No alternative backend is accepted.

## Alternatives rejected

### Patch the historical full worker launcher

Rejected because it would mix the Q6 attention question with native-extension,
worker, model, request, and cache boundaries.

### Import the entire vLLM serving stack

Rejected because broad vLLM import is a later Q7 gate. This gate imports only
the exact registry, backend, backend contract, platform contract, and primitive
modules required to answer the Q6 question.

### Rely on backend auto-selection

Rejected because success could be caused by a silent backend substitution.

### Reuse the accepted vector-add primitive

Rejected because a generic Triton kernel does not prove the vLLM attention
boundary.

### Start a model or worker

Rejected because model and worker budgets remain zero.

## Failure taxonomy

The harness distinguishes:

```text
platform identity mismatch
wheelhouse invalid
runtime installation failure
target import failure
vLLM version mismatch
target-origin mismatch
registry mismatch
registry override detected
backend class import failure
capability rejection
fallback attribution failure
primitive execution failure
SDPA result mismatch
global environment mutation
```

Completed reports remain preserved. The first divergent report is marked
`FAILED_CLOSED`; downstream reports are marked `NOT_EXECUTED`.

## Consequences

### Positive

- One runtime question is isolated from workers, models, and requests.
- Backend attribution is machine-enforced.
- Failure evidence remains diagnostic rather than collapsing into a generic
  vLLM failure.
- The accepted explicit-driver contract remains child-local.
- The implementation is deterministic and locally testable without CUDA.

### Negative

- A direct model-free attention primitive does not prove paged decode attention,
  KV-cache operation, native extensions, worker readiness, or serving.
- A future Kaggle execution and its evidence acceptance still require separate
  authorization and repository tranches.

## Runtime and claim boundary

This implementation authorizes no runtime action.

It does not establish:

```text
attention-backend runtime success
broad vLLM import
native-extension compatibility
worker startup
model loading
inference
cache behavior
measured A/B/C effects
deployment
production readiness
```

## Next gate after merge

```text
DESIGN_AND_MERGE_EXPLICIT_TRITON_ATTENTION_BACKEND_EXECUTION_AUTHORIZATION_V1
```

No execution becomes legal merely because this implementation merges.

## Upstream references

- vLLM `0.19.1` attention registry API
- vLLM `0.19.1` Triton attention backend API
- vLLM `0.19.1` attention backend validation contract
- vLLM `0.19.1` platform `DeviceCapability` contract
