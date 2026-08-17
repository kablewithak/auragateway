# AuraGateway B-vs-D Marker-Diversified Differential Execution Authorization Issuer V1

## Status

`IMPLEMENTED_NOT_ISSUED`

This tranche implements the static transaction-bound execution-authorization issuer for the merged B-vs-D cumulative-length-locked marker-diversified differential.

It does not issue live authority, create a live transaction ID, generate a live governed executable, persist a live platform observation, execute Kaggle, load a model, start a worker, or perform a model request.

## Bound authority

- Authorization-design merge commit: `5c7779465e04ef1fdd3d6cd3d414d357fce3cdca`
- Authorization-design record SHA-256: `77a8140ad6a95da54bc1b21a5844edbbcbc52f53e75d0ba2eaf8de4b55a0d848`
- Implementation merge commit: `a24eedc9d7a65756affc9cde224acdc80fdf7313`
- Implementation review SHA-256: `7278fdf91cef5fd2a19e39f4bc34421c2dce823a42e09aacc7c44ccce7fb53dc`
- Implementation record SHA-256: `795a7cdf5285ba49e5dcc57a76cd46e03f07121359a5f66101692cee41bb2074`
- Successor runtime SHA-256: `fe5bf3cc731d42ead44451cea4298ba1507cbcba28b65fcdbae0a31237868d39`
- Authorization architecture: `TRANSACTION_BOUND_EXECUTION_ARTIFACT`
- Authorization scope: `B_VS_D_CUMULATIVE_LENGTH_LOCKED_MARKER_DIVERSIFIED_DIFFERENTIAL_V1`

## Frozen experiment contract

Variable under test:

`MARKER_DIVERSIFICATION_UNDER_CUMULATIVE_PROMPT_TOKEN_LENGTH_LOCK`

Conditions:

- `B_NEUTRAL_REPEATED_24X`
- `D_NEUTRAL_MARKER_DIVERSIFIED_24X_CUMULATIVE_LENGTH_LOCKED`

Request order:

`B,D,D,B,B,D`

Each condition has three observations. Every observation requires a fresh worker process and teardown before the next observation.

Both conditions remain exactly 899 prompt tokens.

B token SHA-256:

`02f2675a0490d16e3a39de9619ae865a8f73024b26c6f9126bf4dea197d99f68`

D token SHA-256:

`878ecc057fbc92764c7b8bddc3024e12720470b84a72d974ef677c16d1e37e21`

B payload SHA-256:

`1c1ccaad07d7f83eca3c79ae015d231dbe8f3da7d6b055ec10da6070378c4efb`

D payload SHA-256:

`0728e8632e4694cd670e472751154d38dcacc34071d74e1caad8ece6608c8010`

The complete cumulative prompt-token profile remains locked:

`83,117,151,185,219,253,287,321,355,389,423,457,491,525,559,593,627,661,695,729,763,797,831,865,899`

The increment remains 34 tokens.

## Decision contract

B must reproduce the historical `0/3` anchor before D can support mechanistic interpretation.

Predeclared outcomes:

- B `0/3`, D `3/3` -> `MARKER_DIVERSIFICATION_RESTORES_BEHAVIOR_UNDER_CUMULATIVE_LENGTH_LOCK`
- B `0/3`, D `0/3` -> `MARKER_DIVERSIFICATION_INSUFFICIENT_AT_D_REPETITION_LEVEL`
- B `0/3`, D mixed -> `D_CONDITION_UNSTABLE_NO_MECHANISTIC_CLAIM`
- B anchor non-reproduction -> `B_ANCHOR_NONREPRODUCTION_INVALIDATES_INFERENCE`
- invariant failure -> `DIAGNOSTIC_INVALID`

No post-hoc 2/3 interpretation is permitted.

The design does not eliminate marker lexical or semantic novelty, does not establish aligned block recurrence as causal, does not establish exact repetition as the sole or root cause, and does not authorize threshold search.

## Issuer controls

The issuer preserves:

- fresh dynamic SHA-256 authorization challenge;
- exact manual operator retype;
- confirmation bound to exact authorization intent;
- maximum confirmation age of 15 minutes;
- default authorization window of 180 minutes;
- maximum authorization window of 240 minutes;
- canonical authorization bytes;
- transaction ID derived from canonical authorization bytes;
- merged issuer commit binding;
- issuer source identity binding;
- authorization-design identity binding;
- implementation authority binding;
- runtime payload identity binding;
- generator-template identity binding;
- exact runtime/model contract binding;
- exact B-vs-D experiment binding;
- exact 6/6/6 execution budget;
- durable platform-observation forward control;
- deterministic transaction-bound executable generation after future live human authorization;
- explicit terminalization.

The assistant, model, runtime, and issuer automation may not synthesize the human confirmation.

## Execution budget

One future governed transaction permits at most:

- 1 Kaggle session
- 1 Save & Run All
- 1 runtime-install attempt
- 1 runtime import-closure probe
- 6 model requests
- 6 model loads
- 6 worker starts
- 32 output tokens per request
- 0 hidden retries
- 0 replacement observations
- 0 external network requests
- 0 benchmark-trajectory requests
- 0 external spend

## Platform boundary

Required platform:

- accelerator: `T4_X2`
- allocated GPU count: `2`
- Internet: `Off`
- credentials: prohibited
- customer data: prohibited
- external network access: prohibited

Forward control:

`PERSIST_DURABLE_OBSERVATION_BEFORE_SAVE_AND_RUN_ALL`

The durable receipt is created after the transaction-bound artifact and before the one Save & Run All. Console-only observation is insufficient. The receipt is not mounted as runtime authorization input.

## Transport boundary

- authorization-specific Kaggle inputs: `0`
- authorization producer notebooks: `0`
- manual confirmation JSON files: `0`
- runtime authorization filename discovery: prohibited
- permitted Kaggle input roles: `durable_runtime`, `model_snapshot`

## Terminalization

Terminal dispositions:

- `CONSUMED`
- `OUTCOME_UNKNOWN`
- `EXPIRED_UNUSED`
- `CANCELLED_UNUSED`
- `ABANDONED_BEFORE_EXECUTION`

Attempted execution terminalizes authority. Terminal authority is not reusable. Unchanged replay is unauthorized. Multiple observed executions invalidate governed acceptance.

Runtime anti-replay and malicious-operator resistance are not claimed.

## Current state

- `live_authorization_issued=false`
- `runtime_execution_authorized=false`
- `governed_executable_generated=false`
- `platform_observation_persisted=false`
- `kaggle_execution_performed=false`
- `model_requests_performed=0`
- `model_loads_performed=0`
- `worker_starts_performed=0`

## Non-claims

This tranche does not establish:

- live human authorization;
- a live transaction ID;
- a generated live governed executable;
- durable live platform observation;
- Save & Run All authority;
- Kaggle or GPU execution;
- model loading;
- worker startup;
- model requests;
- B anchor reproduction in this tranche;
- D endpoint behavior;
- exact repetition as sole or root cause;
- aligned block recurrence as causal;
- elimination of marker lexical or semantic novelty;
- an exact repetition threshold;
- a prefix-cache defect;
- P5 or P6 requalification;
- final North-Star A/B/C effects;
- deployment or production readiness.

## Next gate

`MERGE_THEN_ISSUE_FRESH_B_VS_D_CUMULATIVE_LENGTH_LOCKED_MARKER_DIVERSIFIED_DIFFERENTIAL_EXECUTION_AUTHORIZATION_V1`

Merging the issuer does not itself grant live runtime authority.
