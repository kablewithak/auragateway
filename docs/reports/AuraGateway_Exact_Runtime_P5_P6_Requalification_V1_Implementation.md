# AuraGateway Exact-Runtime P5/P6 Requalification V1 — Implementation Report

**Checkpoint:** 2026-08-10
**Base main:** `4b3076a62e3f66ff40b59e45d3525bb292c2a1da`
**Implementation state:** `IMPLEMENTED_NOT_EXECUTED`

## Purpose

Implement the frozen exact-runtime behavioral qualification contract without
promoting any runtime claim before governed execution.

## Accepted current authorities

- exact-runtime V5 capability acceptance:
  `b86314bd8c9a71766884ac7143b7fff3198e986dd99c6065814b45c8d1095eb1`
- exact resolution lock:
  `1294394ac476336b103b036d8654a49e4ae78c25c912ca5729cd94f982384f3c`
- V5 semantic-boundary design:
  `1d248baa983edebeda4f0fa95aa5a70c870d18dcba374249c40125cc81e48c75`
- frozen P5/P6 design:
  `4781d9d3dda0c69cdc629a78dbaa94c39e73374914e40d1b48486b7d0e0033a2`

Historical P5/P6 acceptance, review, harness, and template are validated only as
`DESIGN_PRECEDENT_ONLY`.

## Implemented capability sequence

```text
C1 model/tokenizer construction
C2 worker startup
C3 single deterministic request
C4 output contract
P5 exact-runtime prefix-cache behavior
P6 exact-runtime worker/state isolation
```

## P5 implementation

The runtime uses server-side `/tokenize` output to record token count, token IDs,
and token-ID SHA-256.

P5 uses typed deltas for:

- prefix-cache queries;
- prefix-cache hits;
- local compute tokens;
- local cache-hit tokens;
- external KV-transfer tokens;
- cached prompt tokens;
- newly computed prefill tokens.

The decision requires:

- cold request: zero local cache hit and positive local compute;
- warm request: positive attributable local cache reuse and reduced computed
  prefill;
- negative-prefix request: reuse no greater than the proven cacheable common
  token-prefix bound and below warm reuse;
- full-process restart: a new worker generation and zero inherited local cache;
- independent worker: zero prohibited inherited local cache;
- zero external KV transfer for the P5 controls.

Latency is not used as primary mechanism proof.

## P6 implementation

P6 requires:

- disjoint worker process trees;
- worker 1 on GPU 0 and worker 2 on GPU 1;
- distinct loopback endpoints;
- intended and realized routes to agree;
- target-worker request metric movement;
- zero non-target-worker request metric movement;
- no fallback;
- no untracked generation substitution;
- no worker-1 cache inheritance by worker 2;
- retained worker-1 state on worker 1 generation 2;
- exact two-request P6 reconciliation.

## Semantic boundary

Decision functions consume typed observations only. Static AST validation rejects
semantic functions that read evidence-projection helpers or stdout/stderr
presentation fields.

Metamorphic tests assert that changing display-path/excerpt policy does not alter
a `BehaviorDecision`.

## Runtime authorization consumer

The runtime refuses to install the exact runtime until one live authorization is
present and identity-bound. The issuer is intentionally absent from this tranche.

## Action ceiling

```text
runtime install attempts: 1
runtime import-closure probes: 1
model loads: 3
worker starts: 3
model requests: 6
hidden retries: 0
benchmark trajectory requests: 0
network requests: 0
external spend: 0
```

## Non-claims

This implementation does not establish model execution, P5, P6, pilot
eligibility, measured A/B/C eligibility, effect size, quality non-inferiority,
latency improvement, cost improvement, or production readiness.

## Next gate

`DESIGN_AND_MERGE_EXACT_RUNTIME_P5_P6_REQUALIFICATION_V1_EXECUTION_AUTHORIZATION_ISSUER`
