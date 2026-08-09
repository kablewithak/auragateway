# ADR: Implement Exact-Runtime P5/P6 Requalification V1 as a New Sibling Harness

**Date:** 2026-08-10
**Status:** Accepted for repository implementation
**Base main:** `4b3076a62e3f66ff40b59e45d3525bb292c2a1da`

## Context

PR #228 accepted exact-runtime offline capability only. The merged P5/P6 design then
froze a separate behavioral qualification contract for the accepted Torch
`2.11.0+cu129` / vLLM `0.25.1+cu129` line.

Historical governed P5/P6 evidence remains valid only for Torch
`2.10.0+cu129` / vLLM `0.19.1`. Its controls are design precedent, not current
runtime authority.

The current design requires six bounded synthetic model requests:

1. `BASE_COLD`
2. `BASE_WARM`
3. `NEGATIVE_PREFIX`
4. `POST_RESET_COLD`
5. `CROSS_WORKER_COLD`
6. `WORKER1_RETENTION`

It also requires the permanent semantic boundary:

```text
RawRuntimeObservation
-> TypedSemanticObservation
-> BehaviorDecision
-> EvidenceProjection
```

## Decision

Implement a new sibling producer, runtime template, generated notebook, tests,
review, and implementation record under the exact-runtime P5/P6 name.

Do not modify the accepted predecessor harness in place.

The implementation:

- installs the accepted 196-wheel exact runtime into an isolated Python 3.12 venv;
- validates exact Torch, CUDA, Transformers, Triton, vLLM distribution/module,
  native-module, GPU, model, and tokenizer identities;
- starts at most three model-serving worker generations;
- performs at most six synthetic model requests with zero hidden retries;
- uses `/tokenize` to establish token-level prefix identity;
- parses the frozen vLLM `0.25.1` cache-specific metric families into typed
  observations before semantic decisions;
- proves P5 using positive, negative-prefix, reset, and independent-worker controls;
- proves P6 using process, GPU, route, metric-window, generation, retention, and
  request-reconciliation evidence;
- treats `AMBIGUOUS` as a terminal non-PASS state;
- makes evidence projection terminal and tests projection-policy invariance;
- requires a future live, single-use authorization before runtime installation;
- produces immutable bounded evidence for later repository disposition.

## Authorization boundary

This tranche defines the runtime authorization consumer contract but does not
issue authorization.

The generated implementation remains:

```text
IMPLEMENTED_NOT_EXECUTED
runtime_execution_authorized=false
pilot_execution_authorized=false
final_measured_abc_execution_authorized=false
```

The runtime fails closed unless a future `execution_authorization_v1.json` binds:

- the exact runtime-script SHA-256;
- implementation-review SHA-256;
- frozen design-record SHA-256;
- accepted V5 capability SHA-256;
- exact scope and request/worker/model-load budgets;
- `single_use=true`;
- a live timezone-aware issuance/expiry window.

## Alternatives rejected

### Rewrite the historical vLLM 0.19.1 harness in place

Rejected because it would blur runtime lineage and increase the risk that
historical accepted semantics are mistaken for current authority.

### Infer P5 from latency

Rejected because latency cannot distinguish prefix reuse from warm-up,
compilation, scheduler state, or unrelated cache effects.

### Treat two successful workers as P6

Rejected because concurrency alone does not prove route realization or state
isolation.

### Issue authorization in the implementation tranche

Rejected because implementation identity must be merged before a single-use
authority can bind it.

## Consequences

Benefits:

- historical evidence remains immutable;
- current runtime lineage is explicit;
- semantic decisions are inspectable and typed;
- accidental ungoverned execution fails closed;
- PASS, FAIL, and AMBIGUOUS preserve diagnostic value;
- the next authorization issuer can bind exact merged implementation bytes.

Costs:

- additional implementation files and tests;
- version-bound metric semantics must be maintained explicitly;
- the execution path remains unavailable until a separate issuer is merged and
  a fresh live authority is created.

## Next gate

`DESIGN_AND_MERGE_EXACT_RUNTIME_P5_P6_REQUALIFICATION_V1_EXECUTION_AUTHORIZATION_ISSUER`
