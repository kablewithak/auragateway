# ADR: P4/P5 Composition Differential Design V1

**Date:** 2026-08-11
**Status:** Implemented design candidate; merge required
**Decision:** Freeze a same-runtime A/B differential that isolates the P4/P5
message-composition seam before any new execution authority is issued.

## Context

The reconciled transaction reached C3 on the current exact runtime and failed
with:

`model response is not valid JSON`

P5 and P6 were not reached.

The reconciliation classified the failure as:

`P4_P5_COMPOSITION_OUTPUT_CONTRACT_REGRESSION`

with specific classification:

`QUALIFIED_CASE_A_REUSED_AFTER_MATERIAL_MESSAGE_CONTEXT_CHANGE`

That classification remains a high-confidence architectural inference rather
than counterfactual proof.

Historical P4 Case A established useful design precedent:

- V4 exact-object system instruction;
- unconstrained output;
- repetition penalty `1.1`;
- temperature `0`;
- top-p `1`;
- seed `7`;
- maximum output tokens `32`;
- three exact-object responses from three requests.

However, the historical P4 execution used a different final probe object and an
older runtime lineage. It therefore cannot serve as the experimental control
for a causal composition claim on the current runtime.

## Decision

The differential runs both cases on the current accepted P5/P6 exact-runtime
lineage and changes only message composition.

### Case A: SIMPLE_CONTROL

Message shape:

1. current P5/P6 `SYSTEM_PROMPT`;
2. current P5/P6 final canonical JSON object.

The long synthetic cache context and assistant acknowledgement are absent.

### Case B: COMPOSED_P5

Message shape:

1. the same current P5/P6 `SYSTEM_PROMPT`;
2. `SYNTHETIC_CACHE_CONTEXT_A`;
3. `SYNTHETIC_ASSISTANT_ACK`;
4. the same current P5/P6 final canonical JSON object.

The final object for both cases is:

`{"probe":"exact-runtime-p5-p6","value":1}`

The fixed request order is:

`A, B, B, A, A, B`

Each case therefore receives three requests.

## Fixed controls

Both cases must use the same:

- model repository and revision;
- model snapshot;
- current exact-runtime lineage;
- `TRITON_ATTN` backend;
- worker generation;
- temperature `0`;
- top-p `1`;
- repetition penalty `1.1`;
- seed `7`;
- maximum output tokens `32`;
- unconstrained output mode;
- final JSON object.

The variable under test is:

`MESSAGE_COMPOSITION_ONLY`

## Evidence contract

Raw prompts and raw outputs are not retained.

Each request may retain only metadata-safe diagnostics defined by the frozen
design record, including:

- response SHA-256;
- response length;
- finish reason;
- completion token count;
- valid-JSON state;
- exact-object state;
- JSON parse line, column, and position when invalid;
- first and last non-whitespace character classes;
- markdown-fence detection.

## Decision states

`COMPOSITION_REGRESSION_SUPPORTED`

Case A is `3/3` exact-object and Case B is `0/3` exact-object.

`COMPOSITION_HYPOTHESIS_NOT_REPRODUCED`

Case A is `3/3` exact-object and Case B is `3/3` exact-object.

`SIMPLE_CONTROL_NOT_RELIABLE`

Case A is not `3/3` exact-object. Composition cannot be assigned causal
responsibility.

`NON_DETERMINISTIC_OR_AMBIGUOUS`

Any remaining mixed result pattern. Stop and design a bounded Case C before
making a causal or remediation claim.

## Safety boundary

This design:

- does not execute Kaggle;
- does not load a model;
- does not start a worker;
- performs zero model requests;
- does not authorize runtime execution;
- does not authorize a runtime fix;
- does not authorize measured A/B/C execution.

Frozen design record SHA-256:

`5bcea57f47573712c5776fcd7d210584c96ece5cf86d09902cf29453e27e39d1`

## Consequences

The historical P4 Case-A result remains design precedent only.

No new runtime execution becomes legal by merging this design.

No remediation follows automatically from any future differential outcome.

The next gate is:

`IMPLEMENT_AND_MERGE_P4_P5_COMPOSITION_DIFFERENTIAL_V1`
