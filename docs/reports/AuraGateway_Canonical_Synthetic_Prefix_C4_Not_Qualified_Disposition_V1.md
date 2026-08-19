# AuraGateway Canonical Synthetic Prefix C4 NOT_QUALIFIED Disposition V1

## Decision

`DISPOSITIONED_VALID_GOVERNED_C4_NOT_QUALIFIED_EXECUTION`

Saved Kaggle version: `343536641`

The governed C4 execution completed all three predeclared observations under the frozen runtime and transaction-bound authority. The execution itself is valid. The behavioral qualification result is `NOT_QUALIFIED`.

## Accepted observations

- scheduled requests: 3
- completed requests: 3
- exact required objects: 0 / 3
- valid JSON objects: 3 / 3
- `finish_reason=stop`: 3 / 3
- HTTP 200: 3 / 3
- zero-cache baselines: 3 / 3
- distinct fresh worker processes: 3
- identical non-qualifying parsed-object identity across all three observations: true
- hidden retries: 0
- external network requests: 0
- worker teardown: passed
- scratch cleanup: passed

## Claim boundary

This disposition does not establish that the canonical synthetic-prefix design is invalid. It does not establish structural diversity as sufficient or insufficient in general, exact repetition as a sole/root cause, context length as causal, or a model, vLLM, or prefix-cache defect.

The exact semantic content of the non-qualifying object was not retained; only its deterministic canonical identity was retained.

P5 and P6 remain not requalified. Final measured A/B/C was not performed. Production readiness is not established.

## Authority

The single-use authorization is terminal and non-reusable. No unchanged replay or new live execution is authorized by this disposition.

## Next gate

`ANALYZE_C4_NOT_QUALIFIED_OUTPUT_DIVERGENCE_BEFORE_NEW_EXECUTION_V1`
