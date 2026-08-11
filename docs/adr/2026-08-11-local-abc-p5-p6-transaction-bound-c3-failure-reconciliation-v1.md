# ADR: P5/P6 Transaction-Bound C3 Failure Reconciliation V1

**Date:** 2026-08-11
**Status:** Implemented candidate; merge required
**Decision:** Accept the preserved technical failure evidence while rejecting the
transaction as a valid single-use P5/P6 qualification.

## Context

Transaction
`8ad4e628eaffbfc52d46bd958588529e940881937e09ade1c5c6064a755fc9aa`
produced primary Kaggle saved version `341728154`.

The primary execution established:

- runtime source identity: passed;
- exact-runtime installation: passed;
- runtime import closure: passed;
- C1 model/tokenizer construction: passed;
- C2 worker startup: passed;
- one model request performed;
- C3 single-request execution: failed;
- safe failure message: `model response is not valid JSON`;
- P5: not reached;
- P6: not reached.

A second Save Version attempt was also launched under the same transaction and
cancelled. Its Kaggle UI version was `2`; Kaggle did not expose a
`scriptVersionId`.

The transaction was therefore terminalized as:

- disposition: `CONSUMED`;
- execution outcome: `DIAGNOSTIC_INVALID`;
- authorization reusable: `false`;
- runtime execution authorized: `false`.

The preserved custody manifest SHA-256 is:

`3ca422790bdb6ff2a57c922e33f3fd7df01226d71e122f77234400a088c82103`

## Historical evidence

The accepted P3-P6 V5 failure previously reached the same output-contract
failure family and classified the boundary as
`P4_OUTPUT_CONTRACT_HARNESS_WEAKNESS`, specifically
`V5_PROMPT_REGRESSION_WITH_UNCONSTRAINED_GENERATION`.

The later governed P4 output-contract diagnostic selected Case A:

- V4 system prompt;
- repetition penalty `1.1`;
- unconstrained output;
- exact-object validation.

Case A completed `3/3` exact-object responses.

The successor P5/P6 architecture subsequently composed that selected Case-A
contract with the V5-derived long synthetic cacheable context.

## Decision

The invalid single-use transaction is not accepted as P5/P6 qualification.

Its primary execution remains valid technical diagnostic evidence.

The current reconciliation classification is:

`P4_P5_COMPOSITION_OUTPUT_CONTRACT_REGRESSION`

with specific classification:

`QUALIFIED_CASE_A_REUSED_AFTER_MATERIAL_MESSAGE_CONTEXT_CHANGE`

This is a high-confidence architectural inference. It is not counterfactual
experimental proof because the exact failed model output was not retained.

The next experiment must isolate the composition seam rather than rerun the
previous six-case P4 search or immediately alter the production-shaped runtime.

## Consequences

No current runtime remediation is authorized.

No new execution is authorized.

No unchanged replay is authorized.

The next gate is:

`DESIGN_AND_MERGE_P4_P5_COMPOSITION_DIFFERENTIAL_V1`

That diagnostic should compare the previously qualified Case-A message shape
against the current P5 cold-baseline composition while holding the model,
runtime, backend, deterministic generation controls, and request budget fixed.
