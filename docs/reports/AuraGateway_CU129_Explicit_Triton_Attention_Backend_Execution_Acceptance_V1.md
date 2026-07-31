# AuraGateway CU129 Explicit Triton Attention-Backend Execution Acceptance V1

## Accepted execution

```text
Kaggle saved version: 339181603
notebook: ag-cu129-triton-attention-backend-v1
status: PASSED
terminal decision: EXPLICIT_TRITON_ATTENTION_BACKEND_V1_PASSED
```

## Evidence identities

```text
log SHA-256:
0e74f803b508d9f2255582d7c7192e33bf0ec267e32d1be199b0df025af1db38

evidence ZIP SHA-256:
858e84c68703850fcd1651575bbc8223b01f46d5a8aaf39cec7fa91c0c65b3a9

authorization SHA-256:
e3e4a84f4b704ee1594e236c7fc4b152f70928e634bf456d35295ff0e9d96782

consumption SHA-256:
e21591d2f5f2104c36c929513817c789af927318f36290acda6c3a166ad79f07
```

## Proven boundary

The run used two Tesla T4 GPUs and a target runtime containing:

```text
vLLM 0.19.1
Torch 2.10.0+cu129
CUDA build 12.9
Triton 3.6.0
```

The runtime discovered
`AttentionBackendEnum.TRITON_ATTN`, resolved
`vllm.v1.attention.backends.triton_attn.TritonAttentionBackend`, rejected a
registry override, and imported all reviewed modules from the isolated target
runtime.

The capability gate accepted:

```text
Tesla T4
compute capability 7.5
decoder attention
float16
head size 64
block size 16
KV-cache dtype auto
```

The exact backend-owned `context_attention_fwd` primitive executed once. Its
output matched the PyTorch SDPA reference within `atol=0.03` and `rtol=0.03`.
Maximum absolute error was `0.00048828125`.

## Lifecycle

The evidence was captured inside the authorization window. The authorization
was then consumed as `PASSED` for saved version `339181603`; it is not reusable.

## Safety

```text
runtime installations: 1
backend discoveries: 1
backend imports: 1
capability validations: 1
attention primitive attempts: 1
model loads: 0
worker starts: 0
model requests: 0
benchmark trajectories: 0
network requests: 0
hidden retries: 0
global environment mutations: 0
credentials used: false
customer data present: false
external spend: 0
```

## Acceptance

Q6 is accepted. The next legal gate is repository-only design and implementation
of the P3-P6 runtime diagnostic. No runtime execution is authorized by this
acceptance PR.

## Non-claims

The primitive used `causal=false`; causal masking is not proven. Paged decoder
attention, KV-cache behavior, worker startup, model loading, inference, cache
reuse, telemetry attribution, reset, dual-worker isolation, measured A/B/C,
deployment, and production readiness remain unproven.
