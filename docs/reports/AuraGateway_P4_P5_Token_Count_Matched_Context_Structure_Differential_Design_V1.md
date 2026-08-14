# AuraGateway P4/P5 Token-Count-Matched Context-Structure Differential Design V1

## Purpose

Freeze a mechanism-discrimination experiment that separates the original repeated
instruction-like semantics from high exact token-pattern repetition while keeping
all three conditions at exactly 899 prompt tokens.

## Accepted evidence

The design is bound to the governed repetition disposition, its approved review,
the exact current repetition runtime, the qualified tokenizer oracle, the
token-count-matched comparator feasibility record, and the human-reviewed freeze
candidate.

The qualified local tokenizer oracle reproduced the historical control identity
at 117 tokens and the historical failed treatment identity at 899 tokens without
loading the model or issuing a model request.

## Conditions

### A — `A_ORIGINAL_24X_ANCHOR`

Historical original body repeated 24 times.

Prompt tokens: `899`

Token SHA-256:
`6b34448d083e68826cae84c0675876c18d7a70fab53299860b78f2a5a18922b0`

This is the reproduction anchor and contains the original instruction-like
repeated semantics.

### B — `B_NEUTRAL_REPEATED_24X`

One neutral, semantically comparable segment repeated 24 times.

Prompt tokens: `899`

Token SHA-256:
`02f2675a0490d16e3a39de9619ae865a8f73024b26c6f9126bf4dea197d99f68`

Duplicate 16-gram fraction: approximately `0.997506`.

### C — `C_NEUTRAL_DIVERSE_24_SEGMENT`

Twenty-four distinct neutral, semantically comparable segments.

Prompt tokens: `899`

Token SHA-256:
`612e1ada53aba2158536cb0d0e142e3152df7e177ff951a2565385473ec698d4`

Duplicate 16-gram fraction: approximately `0.019950`.

Human review accepted neutrality, naturalness, semantic comparability, and
structural isolation with bounded lexical novelty.

## Frozen composition

All conditions preserve the four-role `system,user,assistant,user` topology, the
accepted V4 system instruction and identical user-context tail, exact assistant
acknowledgement, final canonical JSON object, runtime/model/tokenizer identity,
TRITON_ATTN, prefix caching, block size 16, max-model-len 4096, temperature 0,
top_p 1, repetition penalty 1.1, seed 7, max_tokens 32, stream false,
unconstrained output, parser semantics, and zero hidden retries.

## Starting-state contract

Every observation uses a fresh worker process and requires a zero cached-prefix
baseline. Teardown is mandatory between observations. Cross-observation cache
carry-over is prohibited.

## Request plan

`A, B, C, B, C, A, C, A, B`

Three observations per condition. Each condition has the same mean ordinal
position: `5`.

Future ceiling: nine model requests, nine worker starts, nine model loads, zero
hidden retries, zero replacement observations, zero benchmark trajectory
requests, zero external network requests during governed requests, and zero spend.

## Primary endpoint

`exact_object`

- pass: `3_OF_3_EXACT_OBJECT_TRUE`
- fail: `0_OF_3_EXACT_OBJECT_TRUE`
- mixed: `1_OR_2_OF_3_EXACT_OBJECT_TRUE`

Any mixed condition receives no mechanistic claim.

## Interpretation contract

- A 0/3, B 3/3, C 3/3:
  `REPEATED_INSTRUCTION_LIKE_SEMANTIC_AMPLIFICATION_STRONGLY_IMPLICATED`
- A 0/3, B 0/3, C 3/3:
  `HIGH_EXACT_TOKEN_PATTERN_REPETITION_STRONGLY_IMPLICATED`
- A 0/3, B 0/3, C 0/3:
  `SHARED_LONG_CONTEXT_FACTOR_REMAINS_LIVE`
- A 0/3, B 3/3, C 0/3:
  `DIVERSE_COMPARATOR_SPECIFIC_EFFECT_OBSERVED`
- any 1/3 or 2/3:
  `UNSTABLE_NO_MECHANISTIC_CLAIM`
- A not 0/3:
  `ANCHOR_NONREPRODUCTION_INVALIDATES_MECHANISTIC_INFERENCE`
- infrastructure/evidence invariant failure:
  `DIAGNOSTIC_INVALID`

The B-to-C contrast has a bounded residual lexical-novelty difference. A B-fail /
C-pass result may strongly implicate high exact token-pattern repetition but does
not prove exact repetition as the sole changed representational property.

## Non-claims

The design does not establish exact root cause, exact repetition threshold,
exact-repetition sole causality, semantic-amplification sole causality,
context-length-alone causality, a prefix-cache defect, P5/P6 requalification, or
a North-Star measured A/B/C effect.

No model, worker, GPU, Kaggle, or runtime execution is authorized by this design.

## Next gate

`IMPLEMENT_AND_MERGE_P4_P5_TOKEN_COUNT_MATCHED_CONTEXT_STRUCTURE_DIFFERENTIAL_V1`
