# AuraGateway B-vs-D Cumulative-Length-Locked Marker-Diversified Differential — Execution Authorization Design V1

## Status

`DESIGN_FROZEN_NOT_EXECUTED`

This tranche freezes the static control-plane design for a future single-use B-vs-D execution authorization. It does not implement an issuer, issue live authority, generate a governed executable, execute Kaggle, load a model, start a worker, or perform a model request.

## Frozen Authorization Scope

`B_VS_D_CUMULATIVE_LENGTH_LOCKED_MARKER_DIVERSIFIED_DIFFERENTIAL_V1`

Architecture:

`TRANSACTION_BOUND_EXECUTION_ARTIFACT`

## Bound Current Authorities

The deterministic design record binds the exact current B-vs-D experiment design and merged implementation lineage:

- frozen experiment design SHA-256: `2e07651681d98d604f0e0f6b4e8964906f39b8bfa0e48b8f8fa8e9de431e7ef9`
- merged successor runtime SHA-256: `fe5bf3cc731d42ead44451cea4298ba1507cbcba28b65fcdbae0a31237868d39`
- implementation review SHA-256: `7278fdf91cef5fd2a19e39f4bc34421c2dce823a42e09aacc7c44ccce7fb53dc`
- implementation record SHA-256: `795a7cdf5285ba49e5dcc57a76cd46e03f07121359a5f66101692cee41bb2074`
- implementation source SHA-256, transitively checked through the bound review: `b337da7299e47f7c1b0d691886a505ea2655159e6426f863f699777f7f31cb1c`
- focused implementation test SHA-256, transitively checked through the bound review: `bf61b407eef10b8233084e802128834306676008906dc048c6e3d9bc62f28f77`
- implementation merge/base main commit: `a24eedc9d7a65756affc9cde224acdc80fdf7313`

The design validator uses ancestry semantics for the frozen base commit; it does not require future HEAD to equal the implementation merge commit forever.

## Frozen B-vs-D Contract

Conditions:

- `B_NEUTRAL_REPEATED_24X` — historical failure anchor
- `D_NEUTRAL_MARKER_DIVERSIFIED_24X_CUMULATIVE_LENGTH_LOCKED` — reviewed marker-diversified intervention

Request order:

`B, D, D, B, B, D`

Execution contract:

- observations per condition: `3`
- prompt-token count per condition: `899`
- segments per condition: `24`
- fresh worker process per observation: required
- zero cached-prefix baseline: required
- prior request cache carryover: prohibited
- teardown between observations: required
- hidden retries: `0`
- replacement observations: `0`
- model requests / loads / worker starts: `6 / 6 / 6`
- external network requests: `0`
- benchmark-trajectory requests: `0`
- external spend: `0`

The complete cumulative prompt-token trajectory remains locked from `83` through `899` in exact 34-token increments. The retired assumption that a textual segment boundary must equal a tokenizer boundary remains prohibited.

Generation controls remain:

- `temperature=0`
- `top_p=1`
- `repetition_penalty=1.1`
- `seed=7`
- `max_tokens=32`
- `stream=false`
- unconstrained output
- no `response_format`
- no schema/guided decoding

Pre-request token identity is required before model-request budget consumption. Invalid JSON remains a diagnostic observation rather than silently becoming a hidden retry.

## Frozen Decision Contract

- B `0/3`, D `3/3` → `MARKER_DIVERSIFICATION_RESTORES_BEHAVIOR_UNDER_CUMULATIVE_LENGTH_LOCK`
- B `0/3`, D `0/3` → `MARKER_DIVERSIFICATION_INSUFFICIENT_AT_D_REPETITION_LEVEL`
- B `0/3`, D `1/3` or `2/3` → `D_CONDITION_UNSTABLE_NO_MECHANISTIC_CLAIM`
- B not `0/3` → `B_ANCHOR_NONREPRODUCTION_INVALIDATES_INFERENCE`
- runtime/token/payload/budget/starting-state/teardown/cleanup/evidence invariant failure → `DIAGNOSTIC_INVALID`

No post-hoc `2/3` mechanistic interpretation is permitted.

## Human Authorization Boundary

A later issuer may create live authority only after a fresh human-controlled:

`RETYPE_DYNAMIC_SHA256_CHALLENGE`

The confirmation must bind the exact authorization intent. The runtime, model, issuer, and assistant may not synthesize the human confirmation.

This design tranche performs no live confirmation and issues no live authority.

## Platform and Transport Boundary

Required future platform policy:

- accelerator: `T4_X2`
- allocated GPU count: `2`
- Internet: `Off`
- credentials: prohibited
- customer data: prohibited
- external network access: prohibited

The design preserves:

`PERSIST_DURABLE_OBSERVATION_BEFORE_SAVE_AND_RUN_ALL`

After the transaction-bound executable exists and before the single Save & Run All, a durable platform-observation receipt must bind the transaction to the observed platform state. Console-only observation is insufficient.

Authorization-specific Kaggle inputs, authorization producer notebooks, manual confirmation JSON, and runtime authorization filename discovery remain prohibited.

## Single-Use Boundary

Attempted execution terminalizes authority. Terminal authority is not reusable. Unchanged replay is unauthorized. Multiple observed executions for one transaction invalidate governed acceptance and require reconciliation.

Terminal dispositions remain:

- `CONSUMED`
- `OUTCOME_UNKNOWN`
- `EXPIRED_UNUSED`
- `CANCELLED_UNUSED`
- `ABANDONED_BEFORE_EXECUTION`

Runtime anti-replay and malicious-operator resistance are not claimed.

## Evidence and Privacy Boundary

Expected governed evidence ZIP:

`ag-b-vs-d-cumulative-length-locked-marker-diversified-differential-evidence-v1.zip`

Pre-request journal:

`pre_request_token_identity_journal_v1.json`

Raw prompts and raw model outputs are not retained. Credentials and customer data remain prohibited.

## Non-Claims

This design does not establish:

- live execution authority
- B-anchor reproduction in the future transaction
- D runtime behavior
- exact repetition as the sole or root cause
- aligned 16-token block recurrence as causal
- elimination of marker lexical novelty
- elimination of marker semantic novelty
- an exact repetition threshold
- a prefix-cache defect
- P5 requalification
- P6 requalification
- a measured North-Star A/B/C effect
- production readiness

## Next Gate

After merge and post-merge reconciliation only:

`IMPLEMENT_AND_MERGE_B_VS_D_CUMULATIVE_LENGTH_LOCKED_MARKER_DIVERSIFIED_DIFFERENTIAL_EXECUTION_AUTHORIZATION_ISSUER_V1`
