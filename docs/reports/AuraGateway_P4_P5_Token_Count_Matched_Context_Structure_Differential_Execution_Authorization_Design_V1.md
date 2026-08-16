# AuraGateway P4/P5 Token-Count-Matched Context-Structure Differential — Execution Authorization Design V1

## Status

`DESIGN_FROZEN_NOT_EXECUTED`

This tranche freezes the control-plane design for a future single-use execution authorization. It does not implement the issuer, issue live authority, generate a governed executable, execute Kaggle, load a model, start a worker, or perform a model request.

## Bound Implementation Authority

- implementation merge commit: `019f3c406400f4ecb07b864349369981d4654513`
- frozen experiment design SHA-256: `888bf0a25a974ba2c62892bc999fe0c9f23d2cf845bcd2542c67e2c9bc4ccf03`
- successor runtime SHA-256: `9327d3fef6b1ba2ea8e9d380338e69e6084388b0d365019af3505e8a6a880834`
- implementation review SHA-256: `fe7bd30cc8afdaa318d09a65748f2ae2d214d7c42f83416b666f1da9d8580a1a`
- implementation record SHA-256: `6815a8d3b6a7eb5e88212fd0e280cbfc686f378ab0c98f18e1a05e0de0681b27`

The implementation record transitively binds the frozen experiment design. The authorization design binds the merged runtime, implementation review, and implementation record exactly.

## Authorization Architecture

Selected architecture:

`TRANSACTION_BOUND_EXECUTION_ARTIFACT`

Authorization scope:

`P4_P5_TOKEN_COUNT_MATCHED_CONTEXT_STRUCTURE_DIFFERENTIAL_V1`

A future canonical authorization must bind the merged authorization-design identity, merged issuer identity, merged implementation authorities, runtime payload, runtime/model contract, frozen A/B/C experiment contract, execution budget, platform policy, authorization window, and durable platform-observation contract.

The static repository runtime is not itself executable authority.

## Frozen A/B/C Contract

All conditions remain exactly 899 prompt tokens and 24 context segments.

- A: `A_ORIGINAL_24X_ANCHOR`
- B: `B_NEUTRAL_REPEATED_24X`
- C: `C_NEUTRAL_DIVERSE_24_SEGMENT`

Request order:

`A, B, C, B, C, A, C, A, B`

Prompt-token SHA-256 identities:

- A: `6b34448d083e68826cae84c0675876c18d7a70fab53299860b78f2a5a18922b0`
- B: `02f2675a0490d16e3a39de9619ae865a8f73024b26c6f9126bf4dea197d99f68`
- C: `612e1ada53aba2158536cb0d0e142e3152df7e177ff951a2565385473ec698d4`

Request-payload SHA-256 identities:

- A: `b038763a5a2cb09f0a565dd7d11ac959c42c9c9a53f0f2d5e384edb6531c3a8e`
- B: `1c1ccaad07d7f83eca3c79ae015d231dbe8f3da7d6b055ec10da6070378c4efb`
- C: `8a3d22f50f1956375cfd52f4f01e1843bfe4753da5c76359c47b8da6ecd46f72`

Each observation requires a fresh worker process, zero cached-prefix baseline, pre-request identity persistence, and teardown before the next observation.

## Decision Contract

Condition A must reproduce the historical 0/3 exact-object result before B or C may be used for mechanistic inference.

- A 0/3, B 3/3, C 3/3 → `REPEATED_INSTRUCTION_LIKE_SEMANTIC_AMPLIFICATION_STRONGLY_IMPLICATED`
- A 0/3, B 0/3, C 3/3 → `HIGH_EXACT_TOKEN_PATTERN_REPETITION_STRONGLY_IMPLICATED`
- A 0/3, B 0/3, C 0/3 → `SHARED_LONG_CONTEXT_FACTOR_REMAINS_LIVE`
- A 0/3, B 3/3, C 0/3 → `DIVERSE_COMPARATOR_SPECIFIC_EFFECT_OBSERVED`
- any condition 1/3 or 2/3 → `UNSTABLE_NO_MECHANISTIC_CLAIM`
- A not 0/3 → `ANCHOR_NONREPRODUCTION_INVALIDATES_MECHANISTIC_INFERENCE`
- invariant failure → `DIAGNOSTIC_INVALID`

B→C retains a bounded lexical-novelty caveat. Exact repetition and semantic amplification are not authorized as sole-cause claims.

## Execution Budget

One future governed transaction permits at most:

- 1 Kaggle session
- 1 Save & Run All
- 1 runtime-install attempt
- 1 runtime import-closure probe
- 9 model requests
- 9 model loads
- 9 worker starts
- 32 output tokens per request
- 0 hidden retries
- 0 replacement observations
- 0 external network requests
- 0 benchmark-trajectory requests
- 0 external spend

## Platform Boundary

Required platform policy:

- accelerator: `T4_X2`
- allocated GPUs: `2`
- Internet: `Off`
- external network access: prohibited
- credentials: prohibited
- customer data: prohibited

The design preserves:

`PERSIST_DURABLE_OBSERVATION_BEFORE_SAVE_AND_RUN_ALL`

After the transaction-bound executable exists and before the single Save & Run All, durable evidence must bind the transaction ID, observation timestamp, accelerator, GPU count, Internet state, and capability source.

Console-only platform observation is insufficient. The receipt is not mounted as runtime authorization input. Runtime admission still requires machine-observable GPU topology.

## Human Authorization Boundary

Future live issuance requires:

`RETYPE_DYNAMIC_SHA256_CHALLENGE`

The challenge must be fresh and dynamic. The operator must manually retype it exactly, and the confirmation must bind the exact authorization intent. The assistant, model, runtime, or issuer may not synthesize the human confirmation.

Maximum confirmation age: 15 minutes.

Default authorization window: 180 minutes.

Maximum authorization window: 240 minutes.

## Single-Use Boundary

Attempted execution terminalizes authority. Terminal authority is not reusable. Unchanged replay is not authorized. Multiple observed executions for one transaction invalidate governed acceptance and require reconciliation.

Runtime anti-replay and malicious-operator resistance are not claimed.

## Evidence and Privacy

Expected evidence artifact:

`ag-p4-p5-token-count-matched-context-structure-differential-evidence-v1.zip`

Raw prompts and raw outputs are not retained. Credentials and customer data are prohibited. Terminal evidence must bind authorization, platform observation, saved-version identity, and evidence identity when available.

## Non-Claims

This design does not establish or authorize:

- live execution authority
- Kaggle execution
- model loading or requests
- root cause
- exact repetition as sole cause
- semantic amplification as sole cause
- exact repetition threshold
- context length alone as causal
- prefix-cache defect
- P5/P6 requalification
- North-Star A/B/C effect
- production readiness

## Next Gate

`IMPLEMENT_AND_MERGE_P4_P5_TOKEN_COUNT_MATCHED_CONTEXT_STRUCTURE_DIFFERENTIAL_EXECUTION_AUTHORIZATION_ISSUER_V1`
