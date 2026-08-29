# ADR: Final 342 Execution Producer Closure V1

**Decision ID:** `FINAL_342_EXECUTION_PRODUCER_CLOSURE_V1`
**Date:** 2026-08-29
**Source main:** `b49ab57c41bfd646a5d35f6fa2972f98989fa48e`
**Execution authority:** None

## Context

G11.3A established the final requirements inventory and precedence model. It deliberately
left ten producer obligations unresolved before execution-manifest freeze.

Repository and run-history inspection now provide enough evidence to classify those
obligations without rewriting proven runtime mechanics or building a general benchmark
platform.

The final objective remains one trustworthy, governable 342-trajectory A/B/C execution.
Producer closure exists to protect that experiment, not to become a second product.

## Decision

Adopt `FINAL_342_EXECUTION_PRODUCER_CLOSURE_V1` as the G11.3B design boundary.

The ten G11.3A producer obligations are classified as:

- request transport and worker startup -> `FINAL_342_EXECUTION_PRODUCER_V1`;
- runtime trace to final-manifest binding -> `FINAL_342_EXECUTION_PRODUCER_V1`;
- typed measured evidence bundle -> `FINAL_342_EXECUTION_PRODUCER_V1`;
- attempt/action reconciliation -> `FINAL_342_EXECUTION_PRODUCER_V1`;
- protected measured-review exporter -> `FINAL_342_PROTECTED_REVIEW_EXPORT_V1`;
- primary/secondary failure persistence -> `FINAL_342_EXECUTION_PRODUCER_V1`;
- teardown/cleanup evidence -> `FINAL_342_EXECUTION_PRODUCER_V1`;
- local-vLLM compatibility mapping -> `FINAL_342_EXECUTION_PRODUCER_V1`;
- monetary pricing/cost claim mapping -> `EXPLICITLY_OUT_OF_SCOPE`; and
- typed final analysis inputs -> `FINAL_342_ANALYSIS_CONTRACTS_V1`.

All mapped obligations are `BOUNDED_SUCCESSOR_REQUIRED`.

No obligation is closed by exact reuse alone. Existing components remain valuable as
accepted mechanics, but final semantics require bounded composition or an explicit scope
decision.

## Forest constraint

The implementation must optimize for the final experiment rather than for abstraction.

Therefore:

- do not build a general benchmark platform;
- do not rewrite historical executed runtimes;
- do not copy V2 runtime semantics wholesale;
- reuse accepted mechanics when exact semantics match;
- add no evidence channel without a final claim, eligibility, privacy, or acceptance need.

The remaining implementation can be described in one sentence:

> Build a transaction-bound final-342 producer that composes accepted local-vLLM mechanics
> with G11.1 final control semantics, persists all claim-critical evidence as typed data
> during execution, and keeps protected human-review material behind a separate digest-bound
> privacy boundary.

## Boundary 1: final execution producer

`FINAL_342_EXECUTION_PRODUCER_V1` owns seven obligations.

It may reuse:

- exact-runtime worker lifecycle, runtime validation, telemetry, teardown, and cleanup
  mechanics from the accepted P5/P6 line;
- loopback request and evidence-bundle mechanics from accepted variance-pilot V2;
- route, retry, warm-eligibility, trace-identity, admission, state-mutation, and failure
  semantics from G11.1.

It must not copy V2's no-retry request semantics. The final Constitution permits one bounded
retry after a typed no-response or definite failure, with fixed two-second backoff and no
retry after an ambiguous outcome.

It must consume the frozen 342-run ledger order exactly, bind the final execution-manifest
SHA to every runtime trace, stay inside the 2,736-attempt ceiling, and perform no synthetic
pre-warm or worker-qualification model requests inside final authority.

## Boundary 2: protected measured-review export

`FINAL_342_PROTECTED_REVIEW_EXPORT_V1` is a separate privacy boundary.

It must:

- remain under `.local/auragateway/final-342-protected-review-v1` and outside Git;
- use opaque review IDs;
- support 100 percent primary rubric review;
- support the frozen 25 percent independent double-review sample using seed `20260712`;
- keep reviewers blind to condition, route, latency, cache, and monetary cost information;
- bind a retention/deletion rule before manifest freeze; and
- expose only safe metadata or digests to public evidence.

## Boundary 3: final analysis contracts

`FINAL_342_ANALYSIS_CONTRACTS_V1` must define typed inputs for:

- execution and comparison eligibility;
- quality review and non-inferiority;
- cold/warm runtime endpoint calculation;
- failure-accounted denominators;
- paired `B-A`, `C-B`, and `C-A` analysis; and
- final claim classification.

The final run must not depend on reconstructing claim-critical inputs from free-form logs
after execution.

## Monetary cost scope

Monetary cost comparison is explicitly out of scope for the final experiment.

The Benchmark Constitution requires a frozen pricing schedule only when monetary cost is
reported. Current preflight-v3 removes active pricing fields, the final local-vLLM runtime
has an external-spend ceiling of zero, and no accepted local-Qwen monetary pricing schedule
exists.

Therefore:

```text
MONETARY_COST_COMPARISON_IN_SCOPE=false
MONETARY_COST_EFFECT_CLAIMS_PERMITTED=false
MAXIMUM_EXTERNAL_SPEND=0
```

This does not remove mechanism-proximal or runtime reporting. Newly computed prefill tokens,
warm/cold behavior, latency, TTFT, route realization, failures, and quality remain in scope.

## Monotonic evidence persistence

Historical governed failures established that already-known truth can be lost or masked if
persistence waits for later enrichment.

The final producer therefore uses `MONOTONIC_PHASE_PERSISTENCE_V1`:

```text
transaction admission
-> persist
request attempt reservation
-> persist
transport outcome
-> persist
telemetry and output admission
-> persist
state mutation decision
-> persist
trajectory terminal state
-> persist
worker teardown
-> persist secondary result
scratch cleanup
-> persist secondary result
evidence packaging
-> persist secondary result
authorization terminalization
-> persist separately
```

The first causal failure is preserved independently. Teardown, cleanup, packaging, and
authority-terminalization failures may not replace it.

## Consequences

After this tranche is validated and merged:

- producer-obligation classification is complete;
- nine bounded successor obligations are identified;
- monetary cost comparison is explicitly excluded;
- three implementation boundaries are frozen;
- final producer implementation is still incomplete;
- complete offline producer rehearsal is still incomplete;
- execution-manifest freeze remains prohibited;
- final execution remains unauthorized; and
- effect claims remain prohibited.

## Next gate

`IMPLEMENT_FINAL_342_EXECUTION_PRODUCER_V1`
