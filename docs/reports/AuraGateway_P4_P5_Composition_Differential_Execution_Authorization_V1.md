# AuraGateway P4/P5 Composition Differential Execution Authorization V1

## Status

`IMPLEMENTED_NOT_ISSUED`

This tranche implements the static transaction-bound execution authorization
issuer for the merged P4/P5 composition differential.

No live authorization is issued and no Kaggle execution occurs in this tranche.

## Bound authority

Authorization design merge:

`0ae3c293b474f9a457ce06c7716121bff59af1a6`

Authorization design record:

`f15a2926001dc4c625a6b60111269a1f3e2b6095d825455a0e8e6e0e77ee6ad2`

Differential implementation merge:

`96dea44afa28e1b61c68eb0eccfc91d312bb89e0`

Successor runtime:

`4711f94031bc65ae159dab14412d99cfbd9ecee01b5a2d7d2fd7a2c2b09d7db7`

## Authorization architecture

The issuer implements:

`TRANSACTION_BOUND_EXECUTION_ARTIFACT`

The operator must retype a fresh dynamic SHA-256 challenge generated from the
exact authorization intent.

Canonical authorization bytes derive the transaction ID.

The generated executable embeds the authorization and exact successor runtime.

Authorization-specific Kaggle inputs remain zero.

Authorization producer notebooks remain zero.

Manual confirmation JSON files remain zero.

## Execution ceiling

The future live transaction permits at most:

- one Kaggle session;
- one Save & Run All;
- one runtime installation attempt;
- one runtime import-closure probe;
- one model load;
- one worker start;
- six model requests;
- zero hidden retries;
- zero replacement workers;
- zero external network requests;
- zero benchmark-trajectory requests;
- zero external spend.

## Runtime admission

The generated wrapper verifies before executing the runtime payload:

- transaction identity;
- live authorization window;
- issuer merge identity;
- issuer source identity;
- authorization-design identity;
- implementation authority;
- generator identity;
- exact runtime payload identity;
- exact runtime/model contract;
- exact execution budget;
- exact A/B experiment contract;
- required platform policy;
- two machine-observable GPUs.

No network probe is performed.

## Platform observation

After a live transaction artifact is generated, the operator must freshly
observe Kaggle T4 x2 with Internet Off before the single Save & Run All.

That observation is later bound to the transaction and saved version through
terminalization.

## Terminal lifecycle

Every attempted execution terminalizes authority.

Terminal authority is non-reusable.

`CONSUMED` requires an execution outcome, saved-version identity, and platform
observation.

`OUTCOME_UNKNOWN` preserves an attempted saved version without fabricating an
execution outcome.

The transaction remains terminalizable even if the expected governed evidence
ZIP is absent.

## Non-claims

This implementation does not establish:

- live execution authority;
- Kaggle execution;
- model loading;
- worker startup;
- successful inference;
- the composition hypothesis;
- Case C;
- runtime remediation;
- runtime anti-replay;
- malicious-operator resistance.

## Next gate

`MERGE_THEN_ISSUE_FRESH_P4_P5_COMPOSITION_DIFFERENTIAL_EXECUTION_AUTHORIZATION_V1`
