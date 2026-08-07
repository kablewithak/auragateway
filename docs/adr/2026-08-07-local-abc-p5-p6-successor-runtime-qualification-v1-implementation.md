# ADR: Compose P4 V2 and V5 into P5/P6 Successor Runtime Qualification V1

**Date:** 2026-08-07
**Status:** Implemented candidate; repository validation required before merge
**Decision:** Implement the successor qualification before any measured A/B/C authorization.

## Context

P4 Output-Contract Diagnostic V2 is accepted. Its selected case is A: V4 system
prompt, repetition penalty 1.1, unconstrained output, and exact-object validation.

Historical V4 established same-worker prefix-cache reuse and a full-process restart
reset. It did not establish complete P6 route and metric isolation. V5 contains the
stronger P5/P6 topology, typed route checkpoints, per-worker counters, metric
attribution, and teardown design, but its governed run stopped at P4.

PR #201 reconciled those lines and returned
`GO_FOR_SUCCESSOR_IMPLEMENTATION_WITH_FROZEN_COMPOSITION_RULES`.

The implementation therefore has one job: prove current-line P5 and P6 without
re-running the A-F output selection experiment and without executing an A/B/C
benchmark trajectory.

## Decision

Build `p5_p6_successor_runtime_qualification_v1` as a deterministic producer plus a
single-cell generated Kaggle notebook.

The composition is:

- P4 V2 owns native/environment hardening.
- P4 V2 case A owns the successor P4 output contract.
- V5 owns the P5/P6 resource envelope, worker topology, metric attribution,
  checkpoints, and teardown shape.
- V5's long synthetic deterministic context is retained as the cacheable prefix.
- The final user message remains the canonical case-A object.
- The P4 canary is also the P5 cold request. P5 therefore adds only warm and
  post-restart requests.
- P6 uses two further requests, one per worker.
- Total model requests are bounded to five.

The runtime environment filters CUDA stub/compat paths, removes inherited
`LD_PRELOAD`, prepends target NVIDIA libraries, retains the real driver boundary,
and uses the same environment for import closure and workers.

Native-origin policy is intentionally narrower than historical V5. CUDA stubs fail
closed. The governed `libcusparse` and `libnvJitLink` observations must come from the
target runtime. Other non-stub ambient CUDA libraries are not rejected merely for
being ambient.

Relevant Prometheus metrics fail closed if multiple labeled series for the same
required metric are observed. This prevents accidental aggregation from becoming
worker-attribution evidence.

P6 route proof is transport completion plus worker-local metric attribution. Model
semantic equality is not route proof.

## Request budget

| Stage | Additional model requests | Worker starts | Model loads |
|---|---:|---:|---:|
| P3 canary | 0 | 1 | 1 |
| P4 canary / P5 cold | 1 | 0 | 0 |
| P5 warm + post-restart | 2 | 1 | 1 |
| P6 worker 1 + worker 2 | 2 | 1 | 1 |
| **Maximum** | **5** | **3** | **3** |

The maximum is a ceiling. Failure at P4 stops P5/P6; failure at P5 stops P6.

## Consequences

Positive:
- current-line P5/P6 can be qualified without contaminating measured A/B/C;
- P4/P5 request reuse preserves the five-request ceiling;
- full-process reset remains the cache-reset proof;
- route attribution does not depend on model-generated semantics;
- generated evidence is deterministic and hash-bound.

Trade-offs:
- one P4 request now carries deterministic synthetic context in addition to the
  frozen case-A output contract so it can serve as a meaningful P5 cold baseline;
- the runtime remains a controlled qualification harness, not production routing;
- runtime success still requires a separate single-use authorization and a governed
  execution/acceptance transaction.

## Non-claims

This implementation does not establish current-line P5 or P6 success. It does not
authorize Kaggle execution, measured A/B/C, customer data, network fallback,
deployment, or production readiness.
