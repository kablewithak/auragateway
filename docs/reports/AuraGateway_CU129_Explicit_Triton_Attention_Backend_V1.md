# AuraGateway CUDA 12.9 Explicit Triton Attention Backend V1

## Executive verdict

AuraGateway now has a production-shaped repository implementation for the next
model-free runtime question:

> Can the governed CUDA 12.9 target discover, import, explicitly attribute,
> validate, and execute vLLM `0.19.1` `TRITON_ATTN` on a Tesla T4 without model,
> worker, request, silent fallback, global linker mutation, or CUDA stubs?

Implementation status:

```text
IMPLEMENTED_NOT_EXECUTED
```

Runtime execution authorization:

```text
false
```

## Accepted upstream authority

The implementation binds, rather than replays:

```text
saved version 339127349
EXPLICIT_CUDA_DRIVER_LINK_PATH_CONTRACT_PASSED
accepted and consumed

saved version 339140121
P0_P2_PLATFORM_DIAGNOSTIC_V2_PASSED
accepted and consumed
```

Both unchanged replays remain prohibited.

## Architecture

```text
accepted driver and platform records
→ strict authority projections
→ exact vLLM 0.19.1 backend reference
→ deterministic request and review
→ inspectable Python template
→ deterministic two-cell notebook
→ implementation record
→ focused regression suite
```

The future runtime program isolates five questions:

```text
1. Is the exact governed platform still present?
2. Does the exact wheelhouse install offline?
3. Does TRITON_ATTN resolve to the pinned class with no override?
4. Does the class accept the T4 decoder configuration?
5. Does its exact owned Triton primitive agree with PyTorch SDPA?
```

## Explicit backend contract

```text
registry:
vllm.v1.attention.backends.registry

registry member:
AttentionBackendEnum.TRITON_ATTN

class path:
vllm.v1.attention.backends.triton_attn.TritonAttentionBackend

primitive module:
vllm.v1.attention.ops.triton_prefill_attention

primitive:
context_attention_fwd
```

The harness rejects:

```text
registry overrides
path drift
class drift
backend-name drift
primitive-ownership drift
automatic selection
silent fallback
```

## Capability contract

```text
GPU: Tesla T4
compute capability: 7.5
head size: 64
dtype: float16
KV-cache dtype: auto
block size: 16
attention type: decoder
MLA: false
sparse attention: false
attention sinks: false
multimodal prefix mode: false
per-head quant scales: false
```

## Primitive contract

The model-free primitive uses deterministic Q, K, and V tensors and compares
the exact Triton backend-owned output with PyTorch scaled dot-product attention.

The runtime acceptance threshold is:

```text
atol=0.03
rtol=0.03
```

The evidence records output identities and maximum absolute error. This is a
bounded numerical compatibility check, not a benchmark.

## Failure behavior

The machine-readable taxonomy separates:

```text
platform
wheelhouse
installation
target import
vLLM identity
origin
registry
override
class import
capability
fallback attribution
primitive execution
numerical comparison
environment integrity
```

A failure cannot silently become a broader platform conclusion. Completed
stages remain visible and unexecuted stages remain explicit.

## Determinism and local validation

The implementation package has locally demonstrated:

```text
source compilation passed
template compilation passed
generation passed
fresh semantic validation passed
deterministic notebook generation passed
15 focused regression cases passed
```

These are package-workspace results. Project-mode mypy, repository Ruff, the
full pytest suite, exact candidate staging, commit-tree parity, push, and merge
must still be performed in the authoritative local repository.

## Privacy and safety

```text
customer data: false
credentials: false
network runtime installation: prohibited
model loads: 0
worker starts: 0
model requests: 0
benchmark requests: 0
external spend: 0
```

No raw prompts, model artifacts, credentials, or customer data are introduced.

## Non-claims

This implementation does not prove:

```text
the future Kaggle image matches the accepted image
the target installation will succeed again
the backend imports on the future image
the attention primitive passes
paged decoder attention
KV-cache compatibility
broad vLLM import compatibility
native-extension compatibility
worker readiness
model loading
inference
cache reuse
latency or cost effects
measured A/B/C behavior
deployment
production readiness
```

## Commercial translation

This is an **AI System Evaluation Audit** and **Agent Harness Hardening Sprint**
proof asset.

Buyer pain:

> A GPU runtime fails and the team cannot tell whether the defect belongs to
> the platform, linker, package tuple, backend registry, kernel, model, worker,
> or request path.

Proof asset:

```text
one explicit risk boundary
machine-enforced attribution
bounded action budget
first-divergence taxonomy
immutable evidence design
no hidden fallback
clear claims and non-claims
```

A CTO pays because this prevents expensive model-level debugging before the
underlying backend has been proven and prevents a green result from being
misattributed to an unintended fallback.

## Next gate after merge

```text
DESIGN_AND_MERGE_EXPLICIT_TRITON_ATTENTION_BACKEND_EXECUTION_AUTHORIZATION_V1
```
