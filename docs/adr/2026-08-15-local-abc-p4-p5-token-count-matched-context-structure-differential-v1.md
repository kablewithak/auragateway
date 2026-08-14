# ADR: P4/P5 Token-Count-Matched Context-Structure Differential V1

Date: 2026-08-15

## Status

Accepted for design freeze only. Runtime execution remains unauthorized.

## Context

The governed repetition differential established `CONTROL_1X` 3/3 exact-object
success and `TREATMENT_24X` 0/3 exact-object success on the bound runtime. The
result supports the frozen 24x long/repeated-context condition as necessary
relative to the 1x control, but does not isolate repetition count, context length,
or the exact repeated body as the sole cause.

Static inspection then established three material facts.

First, the 24x prompt is exactly 899 tokens and the 1x prompt is 117 tokens under
the pinned tokenizer. Second, the original repeated body contains instruction-like
semantic content repeated 24 times while the nearest exact JSON instruction remains
topologically close to the final object. Third, cross-request prefix-cache reuse is
not necessary for the observed failure because every governed observation began
from a fresh worker with zero cached-prefix reuse.

A qualified local tokenizer oracle reproduced the historical 117-token and
899-token identities exactly without loading the model. Comparator construction
then produced three 899-token conditions:

- A: the historical original 24x anchor;
- B: 24 identical neutral, semantically comparable segments;
- C: 24 distinct neutral, semantically comparable segments.

B retains extremely high exact repetition. C materially reduces exact token
repetition while preserving total prompt token count, role topology, frozen tail,
assistant acknowledgement, final object, and broad semantic class.

An earlier construction attempt required every C segment to contribute exactly
34 tokens. That constraint was rejected after it stranded the final segment. It
was a construction convenience, not a causal invariant.

## Decision

Freeze a three-condition mechanism-discrimination design with exactly three
observations per condition and a fresh worker process per observation.

The order is:

`A, B, C, B, C, A, C, A, B`

Each condition occupies three positions whose ordinal sum is 15. This balances
average execution position across A, B, and C without adding retries or replacement
observations.

The primary endpoint is `exact_object`.

- `3_OF_3_EXACT_OBJECT_TRUE` is a condition pass.
- `0_OF_3_EXACT_OBJECT_TRUE` is a condition fail.
- `1_OR_2_OF_3_EXACT_OBJECT_TRUE` is mixed and supports no mechanistic claim.

Condition A is the historical reproduction anchor. If A is not 0/3 exact-object,
B and C receive no mechanistic interpretation.

The A-to-B contrast primarily tests the original repeated semantic and
instruction-like body against a neutral repeated body. The B-to-C contrast
primarily tests very high exact token-pattern repetition against substantially
lower exact repetition while preserving broad semantic comparability and 899 total
prompt tokens.

Lexical novelty necessarily increases in C when exact repetition is reduced.
Therefore B-to-C can strongly implicate exact token-pattern repetition but cannot
establish it as the sole changed representational property.

## Alternatives rejected

1. **Per-segment 34-token equality.** Rejected because it overconstrains the
   construction without strengthening the causal claim.
2. **Random or unrelated 899-token filler.** Rejected because topic and semantic
   drift would create a larger confound than the repetition contrast.
3. **Threshold search.** Rejected because the current question is mechanism
   discrimination, not threshold estimation.
4. **Worker reuse across observations.** Rejected because request-history/cache
   state would become an additional varying factor.
5. **Immediate model execution.** Rejected because design, implementation, and
   authorization remain separate governed transitions.

## Consequences

A future execution ceiling becomes nine model loads, nine worker starts, and nine
model requests, with zero hidden retries, zero replacement observations, zero
external network requests during governed requests, and zero spend.

The design can distinguish whether the original repeated semantics, high exact
repetition, or a factor shared across all 899-token conditions remains the more
plausible boundary. It still cannot establish exact root cause, exact threshold,
sole repetition causality, sole semantic-amplification causality, a prefix-cache
defect, P5/P6 requalification, or a North-Star measured A/B/C effect.

The qualified tokenizer receipt, comparator feasibility record, and human-reviewed
freeze candidate are preserved byte-for-byte as design authorities.

## Next gate

`IMPLEMENT_AND_MERGE_P4_P5_TOKEN_COUNT_MATCHED_CONTEXT_STRUCTURE_DIFFERENTIAL_V1`
