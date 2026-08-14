# AuraGateway P4/P5 Cache-Context Repetition Differential Execution Authorization V1

## Status

`IMPLEMENTED_NOT_ISSUED`

This tranche implements the transaction-bound authorization issuer for one future governed execution of the frozen P4/P5 cache-context repetition differential. It does not issue live authority, generate a live governed notebook, persist a live Kaggle platform observation, execute Kaggle, load a model, start a worker, or perform a model request.

## Bound authorization design

Authorization-design merge commit:

`0ad27e48e72f91f52ca48927a66bbe44f099e258`

Authorization-design record SHA-256:

`900b76c0cf8f833733f63c006e4aa489f9581d80260f4f30f6a4b9161c973a77`

Authorization architecture:

`TRANSACTION_BOUND_EXECUTION_ARTIFACT`

Authorization scope:

`P4_P5_CACHE_CONTEXT_REPETITION_DIFFERENTIAL_V1`

## Bound differential implementation

Implementation merge commit:

`658a21516fa6b1cc72bd53c2c65e51aae88b4d79`

Successor runtime SHA-256:

`dfa0e7ea48eaf21dd6d3faf97b0440dda19817dec18de7c17d720c9185569a4b`

Implementation review SHA-256:

`6bf7595e9dda3793f94bf866e0feff8db31cfe2c4c9cd7e3f4941c973a4ea2a4`

Implementation record SHA-256:

`31628aef52b292236bbaf9a787fd1f47ca3751a1416cf916b51fc354258e4a6c`

## Human authorization boundary

Live issuance requires `RETYPE_DYNAMIC_SHA256_CHALLENGE`. The issuer prepares one exact authorization intent, derives a fresh SHA-256 challenge from its canonical bytes, prints the bound scope and budgets, and requires exact manual operator retype. The model, runtime, issuer automation, or assistant may not synthesize the confirmation.

Maximum confirmation age is 15 minutes. The default authorization window is 180 minutes and the maximum window is 240 minutes.

No live authorization is issued by this implementation tranche.

## Frozen differential contract

Variable under test: `CACHE_CONTEXT_REPETITION_COUNT`.

Control: `CONTROL_1X` with one repetition.

Treatment: `TREATMENT_24X` with 24 repetitions.

Request order: `CONTROL_1X, TREATMENT_24X, TREATMENT_24X, CONTROL_1X, CONTROL_1X, TREATMENT_24X`.

There are three observations per condition. Every observation requires a fresh worker process, zero cached-prefix baseline, pre-request token/payload identity persistence, exactly one bounded model request, and teardown before the next observation.

The 24x treatment remains bound to token count `899`, token SHA-256 `6b34448d083e68826cae84c0675876c18d7a70fab53299860b78f2a5a18922b0`, and payload SHA-256 `b038763a5a2cb09f0a565dd7d11ac959c42c9c9a53f0f2d5e384edb6531c3a8e`.

No threshold search, runtime remediation, assistant-topology discriminator, or measured North-Star A/B/C execution is authorized.

## Execution budget

One governed transaction permits at most:

- 1 Kaggle session
- 1 Save & Run All
- 1 runtime-install attempt
- 1 runtime import-closure probe
- 6 model requests
- 6 model loads
- 6 worker starts
- 0 hidden retries
- 0 replacement workers
- 0 external network requests
- 0 benchmark-trajectory requests
- 0 external spend

## Durable platform observation

The issuer preserves `PERSIST_DURABLE_OBSERVATION_BEFORE_SAVE_AND_RUN_ALL`. After the transaction-bound artifact exists and before Save & Run All, a durable receipt must bind transaction ID, platform observation timestamp, accelerator, allocated GPU count, Internet state, and capability source. Console-only observation is insufficient. The receipt is not a runtime authorization input. Runtime admission still verifies machine-observable GPU topology.

## Single-use lifecycle

Transaction ID derives from `SHA256(CANONICAL_AUTHORIZATION_BYTES)`. Attempted execution terminalizes authority. Terminal authority is not reusable. Unchanged replay is unauthorized. Multiple observed executions invalidate governed acceptance and require reconciliation. Runtime anti-replay and malicious-operator resistance are not claimed.

Terminal dispositions remain `CONSUMED`, `OUTCOME_UNKNOWN`, `EXPIRED_UNUSED`, `CANCELLED_UNUSED`, and `ABANDONED_BEFORE_EXECUTION`.

## Evidence boundary

Raw prompts and raw model outputs are not retained. Credentials and customer data are prohibited. The runtime preserves metadata-safe pre-request token identity evidence and the terminal lifecycle binds transaction, durable platform observation, saved-version identity, and evidence identity where available.

## Current state

- live authorization issued: false
- runtime execution authorized: false
- platform observation persisted: false
- Kaggle execution performed: false
- model requests performed: 0
- model loads performed: 0
- worker starts performed: 0

## Non-claims

This implementation does not establish live human authorization, a live transaction ID, a generated governed notebook, durable Kaggle platform observation, Save & Run All authority, Kaggle execution, the 1x-vs-24x behavioral result, an exact repetition threshold, root cause, P5/P6 requalification, measured North-Star support, or production readiness.

## Next gate

`MERGE_THEN_ISSUE_FRESH_P4_P5_CACHE_CONTEXT_REPETITION_DIFFERENTIAL_EXECUTION_AUTHORIZATION_V1`
