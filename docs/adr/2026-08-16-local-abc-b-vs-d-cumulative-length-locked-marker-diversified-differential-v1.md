# ADR: B-vs-D Cumulative-Length-Locked Marker-Diversified Differential V1

Date: 2026-08-16

## Status

Accepted for design freeze only. Runtime execution remains unauthorized.

## Context

The governed token-count-matched A/B/C diagnostic produced A=0/3, B=0/3,
and C=3/3 exact-object responses at exactly 899 prompt tokens per condition.
That result strongly implicates high exact token-pattern repetition, but the
B-to-C contrast also introduced broad lexical novelty.

Static follow-up inspection narrowed the remaining representational structure.
B retained very high 34-token periodicity and repeated aligned 16-token blocks,
while C substantially reduced both. Cross-request prefix-cache reuse remained
zero and therefore did not explain the observed endpoint difference.

A first marker-diversified feasibility harness incorrectly assumed that each
textual segment join must coincide with a tokenizer boundary. Qwen BPE can merge
across concatenated text joins, so that invariant was rejected. The corrected
feasibility harness instead locks the complete cumulative prompt-token count
profile against governed B without making textual-boundary claims.

The reviewed D comparator changes only the neutral marker noun in the exact B
sentence template. It preserves the same 24-segment count and cumulative token
profile from 83 tokens through +34 tokens per addition to exactly 899 tokens.

Human review accepted neutrality, naturalness, semantic comparability to B,
marker-only textual change, absence of instruction-like semantics, forbidden-term
absence, and structural isolation with bounded marker lexical and semantic novelty.

The user explicitly approved this reviewed comparator for design freeze.

## Decision

Freeze a two-condition B-vs-D mechanism-discrimination design.

- B is the governed failure anchor and historically produced 0/3 exact-object.
- D is the marker-diversified intervention and has not been executed.

The frozen order is:

`B, D, D, B, B, D`

Each condition has exactly three observations. The unavoidable one-position
imbalance is bounded: B occupies ordinals 1,4,5 and D occupies 2,3,6.

The primary endpoint is `exact_object`.

- `3_OF_3_EXACT_OBJECT_TRUE` is a condition pass.
- `0_OF_3_EXACT_OBJECT_TRUE` is a condition fail.
- `1_OR_2_OF_3_EXACT_OBJECT_TRUE` is mixed and supports no mechanistic claim.

B must reproduce 0/3 before D receives mechanistic interpretation.

## Interpretation contract

If B=0/3 and D=3/3, marker-only diversification restores behavior while the
complete cumulative prompt-token trajectory remains fixed. This strengthens a
repetition-sensitive representational mechanism and weakens token-length
trajectory alone as an explanation.

That outcome still does not isolate exact n-gram repetition from aligned
16-token block recurrence or marker novelty because those properties move
together under the intervention.

If B=0/3 and D=0/3, D-level diversification is insufficient. Given the already
governed C success, a stronger diversification or threshold-like effect remains
live, but no exact threshold is established.

Any mixed D result receives no mechanistic claim. Any B non-reproduction
invalidates D mechanistic interpretation.

## Alternatives rejected

1. **Reuse C as the intervention.** Rejected because C changes full sentence
   structure and lexical content, creating a broader residual confound.
2. **Text-segment boundary token-phase locking.** Rejected because textual joins
   are not valid tokenizer-boundary authorities under BPE.
3. **Immediate threshold search.** Rejected because the current question is
   whether a much narrower marker-only intervention changes behavior.
4. **Worker reuse.** Rejected because prior request/cache state would become a
   second varying factor.
5. **Immediate execution.** Rejected because design, implementation, and
   authorization remain separate governed transitions.

## Consequences

A future execution ceiling becomes six model loads, six worker starts, and six
model requests, with zero hidden retries, zero replacement observations, zero
external network requests during governed requests, and zero spend.

No exact root cause, exact threshold, sole repetition causality, aligned-block
causality, prefix-cache defect, P5/P6 requalification, North-Star measured A/B/C
effect, or production readiness is established by this design.

The feasibility record, human semantic-review record, and user-approved freeze
candidate are immutable byte-preserved authorities.

## Next gate

`IMPLEMENT_AND_MERGE_B_VS_D_CUMULATIVE_LENGTH_LOCKED_MARKER_DIVERSIFIED_DIFFERENTIAL_V1`
