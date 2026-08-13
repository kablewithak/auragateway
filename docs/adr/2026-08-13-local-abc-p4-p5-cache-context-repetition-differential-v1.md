# ADR: P4/P5 Cache-Context Repetition Differential V1

Date: 2026-08-13

## Status

Accepted for design freeze only. Runtime execution remains unauthorized.

## Context

The governed composition differential established SIMPLE_CONTROL 3/3 exact-object
success and COMPOSED_P5 0/3 exact-object success on the current runtime. Replacing
the historical V5 cache-context instruction tail with the accepted V4 instruction
did not restore the composed C3 contract.

The merged static inspection selected cache-context repetition count as the
smallest unresolved discriminator: control 1x versus treatment 24x with the rest
of the composition frozen.

Because prefix caching is enabled, reusing one continuously running worker would
allow earlier requests to influence later cache state. That would mix repetition
count with request-history/cache-state effects.

Historical governed P5 evidence establishes full worker-process restart as a
valid reset precedent in the predecessor lineage: cold cached-prefix tokens were
0, warm reuse was positive, and post-restart cached-prefix tokens returned to 0.

## Decision

Every observation begins from a fresh worker process.

The order is:

`1x, 24x, 24x, 1x, 1x, 24x`

Each observation requires fresh worker identity, a zero cached-prefix baseline,
pre-request token identity persisted before the model request, exactly one model
request, and successful teardown before the next observation.

Namespace-only reset and cross-observation cache carry-over are prohibited.

Prefix variant A, four-role topology, V4 instruction, assistant acknowledgement,
final object, runtime/model/tokenizer identity, cache configuration, generation
controls, parser semantics, and zero-retry policy remain frozen.

The 24x treatment must reproduce the exact historical failed C3 token and request
payload identities.

## Consequences

The future execution ceiling becomes six model loads, six worker starts, and six
model requests. This higher cost is accepted because it buys equivalent cold
starting state for each causal observation.

A 1x 3/3 versus 24x 0/3 result may support necessity only relative to the 1x
control. It does not establish that exactly 24 repetitions are the causal
threshold, that context length alone is causal, or that prefix caching is
defective.

## Next gate

`IMPLEMENT_AND_MERGE_P4_P5_CACHE_CONTEXT_REPETITION_DIFFERENTIAL_V1`
