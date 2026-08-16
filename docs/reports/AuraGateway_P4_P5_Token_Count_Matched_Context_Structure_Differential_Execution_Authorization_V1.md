# AuraGateway P4/P5 Token-Count-Matched Context-Structure Differential Execution Authorization V1

## Status

`IMPLEMENTED_NOT_ISSUED`

This tranche implements the transaction-bound execution-authorization issuer for the merged P4/P5 token-count-matched context-structure differential V1. Static generation and validation are inert. This tranche does not issue live authority, generate a live governed notebook, persist a live platform observation, execute Kaggle, load a model, start a worker, or perform a model request.

## Bound Authorities

- Authorization-design merge commit: `76f82a4bfeb583a6839ae945f53954e7dcabcfbf`
- Authorization-design record SHA-256: `6ba28cdb0f2d489c5de9171ab08edad6403d9adb058fb6b84caa61e03d1b69a4`
- Implementation merge commit: `019f3c406400f4ecb07b864349369981d4654513`
- Successor runtime SHA-256: `9327d3fef6b1ba2ea8e9d380338e69e6084388b0d365019af3505e8a6a880834`
- Implementation review SHA-256: `fe7bd30cc8afdaa318d09a65748f2ae2d214d7c42f83416b666f1da9d8580a1a`
- Implementation record SHA-256: `6815a8d3b6a7eb5e88212fd0e280cbfc686f378ab0c98f18e1a05e0de0681b27`
- Authorization architecture: `TRANSACTION_BOUND_EXECUTION_ARTIFACT`
- Authorization scope: `P4_P5_TOKEN_COUNT_MATCHED_CONTEXT_STRUCTURE_DIFFERENTIAL_V1`

## Issuer Controls

The issuer implements:

- fresh dynamic SHA-256 authorization challenge;
- exact manual operator retype;
- confirmation bound to the exact authorization intent;
- maximum confirmation age of 15 minutes;
- default authorization window of 180 minutes;
- maximum authorization window of 240 minutes;
- canonical compact sorted JSON authorization bytes;
- transaction ID `SHA256(CANONICAL_AUTHORIZATION_BYTES)`;
- merged issuer commit and issuer-source binding;
- authorization-design and implementation authority binding;
- runtime-payload and generator-template binding;
- exact runtime/model, budget, experiment, and platform binding;
- deterministic transaction-bound notebook generation;
- durable platform-observation forward control;
- explicit terminalization.

The static repository runtime is not itself executable authority.

## Frozen A/B/C Experiment Contract

All three conditions have exactly `899` prompt tokens and use the frozen four-message topology.

- A: `A_ORIGINAL_24X_ANCHOR`
- B: `B_NEUTRAL_REPEATED_24X`
- C: `C_NEUTRAL_DIVERSE_24_SEGMENT`
- observations per condition: `3`
- total observations: `9`
- request order: `A,B,C,B,C,A,C,A,B`
- fresh worker per observation: `true`
- prior-request cache carryover: prohibited
- pre-request token and payload identity checks: required
- maximum output tokens per request: `32`
- repetition penalty: exactly `1.1`
- threshold search: unauthorized
- runtime remediation: unauthorized
- P5/P6 requalification: unauthorized
- North-Star A/B/C effect claim: unauthorized

Condition A must reproduce the historical `0/3` result before B or C can support mechanistic interpretation. Any mixed condition result yields no mechanistic claim.

Predeclared stable outcomes:

- A0/B3/C3 → `REPEATED_INSTRUCTION_LIKE_SEMANTIC_AMPLIFICATION_STRONGLY_IMPLICATED`
- A0/B0/C3 → `HIGH_EXACT_TOKEN_PATTERN_REPETITION_STRONGLY_IMPLICATED`
- A0/B0/C0 → `SHARED_LONG_CONTEXT_FACTOR_REMAINS_LIVE`
- A0/B3/C0 → `DIVERSE_COMPARATOR_SPECIFIC_EFFECT_OBSERVED`

## Execution Budget

One future governed transaction permits at most:

- 1 Kaggle session;
- 1 Save & Run All;
- 1 runtime-install attempt;
- 1 runtime import-closure probe;
- 9 model requests;
- 9 model loads;
- 9 worker starts;
- 32 output tokens per request;
- 0 hidden retries;
- 0 replacement observations;
- 0 external network requests;
- 0 benchmark-trajectory requests;
- 0 external spend.

## Platform and Human Boundaries

Required platform remains `T4_X2`, exactly two allocated GPUs, Internet Off, no external network access, no credentials, and no customer data.

After the transaction-bound executable exists and before the single Save & Run All, the operator must persist the durable platform observation controlled by:

`PERSIST_DURABLE_OBSERVATION_BEFORE_SAVE_AND_RUN_ALL`

Console-only observation is insufficient. The platform receipt is not mounted as runtime authorization input. Runtime admission still performs a machine-observable GPU topology check.

Future live issuance requires `RETYPE_DYNAMIC_SHA256_CHALLENGE`. The assistant, model, runtime, or issuer automation may not synthesize the operator confirmation.

## Single-Use and Terminalization

Attempted execution terminalizes authority. Terminal authority is not reusable. Unchanged replay is unauthorized. Multiple observed executions for the same transaction invalidate governed acceptance.

Terminal dispositions:

- `CONSUMED`
- `OUTCOME_UNKNOWN`
- `EXPIRED_UNUSED`
- `CANCELLED_UNUSED`
- `ABANDONED_BEFORE_EXECUTION`

Runtime anti-replay and malicious-operator resistance are not claimed.

## Current Non-Authorization State

- `live_authorization_issued=false`
- `runtime_execution_authorized=false`
- `governed_executable_generated=false`
- `platform_observation_persisted=false`
- `kaggle_execution_performed=false`
- `model_requests_performed=0`
- `model_loads_performed=0`
- `worker_starts_performed=0`

## Next Gate

`MERGE_THEN_ISSUE_FRESH_P4_P5_TOKEN_COUNT_MATCHED_CONTEXT_STRUCTURE_DIFFERENTIAL_EXECUTION_AUTHORIZATION_V1`

Merge of this issuer implementation does not itself issue live authority.
