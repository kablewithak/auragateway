# ADR: Exact-Runtime P5/P6 Requalification Design V1

## Status

PROPOSED FOR REPOSITORY ACCEPTANCE. Design-only. No runtime authority.

## Context

PR #228 accepted the exact offline runtime capability with `qualification_scope=CAPABILITY_ONLY`.
Model construction, worker startup, one deterministic request, P5 cache behavior, and P6
worker/state isolation remain unproved on Torch 2.11.0+cu129 / vLLM 0.25.1+cu129.

The predecessor governed P5/P6 PASS at saved version 340976295 remains valid evidence for
Torch 2.10.0+cu129 / vLLM 0.19.1. It is design precedent only and cannot qualify the current
runtime line.

## Decision

Freeze a six-request, three-worker-start behavioral qualification contract before implementing
or authorizing model execution.

The semantic pipeline remains:

`RawRuntimeObservation -> TypedSemanticObservation -> BehaviorDecision -> EvidenceProjection`

Public, sanitized, truncated, or formatted evidence cannot flow back into semantic decisions.

### P5

P5 requires cache-specific attributable token evidence plus four controls:

1. same-worker identical-prefix positive control;
2. same-worker changed-prefix negative control;
3. independent-worker identical-prefix negative control;
4. full-process-restart reset control.

Latency is secondary evidence only.

The exact vLLM 0.25.1 semantic contract uses prefix-cache query/hit counters, prompt-token
source counters (`local_compute`, `local_cache_hit`, `external_kv_transfer`), cached prompt
tokens, and the prefill-KV-computed-token histogram. Missing or ambiguous relevant metric
series do not become zero.

Prefix identity is token-level. The implementation must use the server `/tokenize` boundary
and preserve token IDs, count, SHA-256, common-prefix length, cache-block size, and the
cacheable common-prefix bound.

### P6

P6 requires explicit worker identity, generation, process tree, port, GPU realization, intended
route, realized route, metric endpoint, request identity, and output provenance. Successful
responses alone do not prove isolation.

### Execution ceiling

- model requests: 6
- worker starts/model loads: 3
- hidden retries: 0
- replacement workers: 0
- benchmark trajectories: 0
- external spend: 0

## Consequences

The next legal gate is implementation of the frozen design. Runtime authorization remains a
separate later tranche after implementation is locally validated and merged.
