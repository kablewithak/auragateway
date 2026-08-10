# ADR: Preserve the Exact-Runtime P5/P6 Authority Failure Before Remediation

## Status

Accepted for failure-governance preservation. No new runtime execution is authorized.

## Context

Governed Kaggle saved version `341454766` terminated at the authorization
boundary before runtime installation. The producer evidence reported
`AUTHORITY_FAILURE`, `authorization=null`, and zero runtime-install, model-load,
worker-start, model-request, network-request, and benchmark-trajectory counters.

A metadata-only inspection in saved version `341466979` reproduced
the intended three-input setup without GPU/runtime execution. The current consumer
pattern:

`*/execution_authorization_v1.json`

returned zero candidates. Recursive diagnostic discovery returned exactly one
candidate at:

`datasets/kabomolefe/ag-p5-p6-execution-authorization-v1/execution_authorization_v1.json`

The candidate was a regular canonical JSON file, matched all checked governed
authorization metadata, and had SHA-256 `e9c1b58aedfccee3f36349bf063d5f1267721b8f395699a6c325304d32c20a2c`.

The single-use authorization has since been terminalized as `CONSUMED` with
outcome `FAILED` for saved version `341454766`. Its terminal receipt
SHA-256 is `e3a3c0519fff010576f1674adf09c5dafa13b013b04e670b2510204c81f7e4b5`.

## Decision

Preserve the failure as an accepted diagnostic failure before changing the
runtime consumer.

Classification:

`AUTHORIZATION_DISCOVERY_CONTRACT_FALSE_NEGATIVE`

Failure depth:

`EARLY_CONTROL_PLANE`

The failure does not establish runtime incompatibility and does not establish
any P5 or P6 result.

The governance package preserves:

- the failed evidence ZIP and terminal log;
- all failed evidence members in queryable form;
- the inspection ZIP and terminal log;
- all inspection evidence members in queryable form;
- exact authorization and terminal-receipt identities;
- the execution-grounded semi-formal reasoning certificate;
- a machine-readable acceptance record and review;
- a fail-closed consumed-authorization reuse guard.

The exact lifecycle JSON bytes are copied from the local operational paths into
the evidence vault only after their SHA-256 and size match the governed
identities. Existing different bytes are never overwritten.

## Alternatives rejected

### Treat the result as exact-runtime incompatibility

Rejected. Runtime installation and all downstream capability stages were
`NOT_RUN`.

### Reuse the consumed authorization

Rejected. The authorization is terminal and non-reusable.

### Patch the consumer with a global recursive filename search

Rejected as the automatic fix. The inspection proves that the current shallow
pattern is wrong, but historical AuraGateway evidence has already shown that
unscoped global filename uniqueness can create namespace-collision false
negatives. Remediation must resolve a governed producer/root before exact
bounded-file validation.

### Skip failure preservation and go directly to another authorization

Rejected. That would discard the diagnostic lineage and repeat an already
disproved readiness assumption.

## Consequences

The repository can now distinguish:

- accepted exact-runtime offline capability from this transport failure;
- authorization producer validity from authorization consumer discovery;
- an early diagnostic failure from a P5/P6 capability result;
- consumed authority from future fresh authority.

No runtime, pilot, or final measured A/B/C execution authority is created.

## Next gate

`DESIGN_AND_MERGE_AUTHORIZATION_TRANSPORT_DISCOVERY_REMEDIATION_V1`
