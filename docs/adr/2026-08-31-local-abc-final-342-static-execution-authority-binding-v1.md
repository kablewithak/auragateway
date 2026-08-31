# ADR: Final-342 Static Execution Authority Binding V1

Date: 2026-08-31

## Status

Proposed for acceptance.

## Context

PR #333 completed the two-stage execution-manifest freeze and merged it with history
preservation. The accepted repository state now contains:

- frozen manifest semantic SHA-256
  `11b4ef75a6a44df51b445c4421290e41ee0994a6143d2e2d8bc034130f35129b`;
- frozen manifest file SHA-256
  `74ce9ada48c2a788ddba9c4cbf2eeba61ab68937e04916b044b567c9b239cc0c`;
- first-containing commit
  `078c1da32fe7c1ee8ff5a8661e5f38e588782abc`;
- post-commit custody commit
  `3746be6a912e7d2f30a88d829a9cff7dbda53c87`;
- repository manifest-freeze promotion;
- no live execution authorization.

The accepted G11.0 architecture requires the next boundary to be static authority binding,
followed by single-use issuer qualification, fresh platform readiness and human authority,
and only then one governed final-342 execution.

## Decision

Create a deterministic, non-authorizing static execution-authority binding.

The binding does not issue permission to execute. It identifies the exact frozen execution
subject that any later issuer qualification must accept without drift.

The binding is anchored to accepted main:

`12a57d5ee101336d1716671cb2d7c8a016f33d2e`

It binds the exact Git identities and bytes for:

1. the frozen final-342 execution manifest;
2. the post-commit custody receipt;
3. the accepted final runtime architecture;
4. the non-authorizing runtime core;
5. the transaction-wrapper rehearsal implementation;
6. the transaction-wrapper template; and
7. the final measured evidence producer.

## Execution subject

The only bound authorization scope is:

`FINAL_342_TRANSACTION_BOUND_MEASURED_ABC_V1`

The execution budget remains:

```text
PLANNED_TRAJECTORIES=342
PLANNED_TURNS=1368
MAXIMUM_REQUEST_ATTEMPTS=2736
MAXIMUM_RETRIES_AFTER_INITIAL_ATTEMPT=1
HIDDEN_RETRIES_PERMITTED=false
REPLACEMENT_CASES_PERMITTED=false
EXTRA_AUTHORITY_CANARY_REQUESTS_PERMITTED=false
EXTRA_WORKER_QUALIFICATION_REQUESTS_PERMITTED=false
EXTERNAL_SPEND_CEILING=0
```

The final manifest identity is required on every runtime trace. Route realization remains
derived from the frozen planned-run route schedule. Both route families use the same local
Qwen model alias and loopback vLLM transport.

## Authority boundary

Static binding is not live issuance.

```text
STATIC_AUTHORITY_BINDING_COMPLETE=true
EXECUTION_MANIFEST_FREEZE_IS_LIVE_AUTHORITY=false
STATIC_BINDING_IS_LIVE_ISSUANCE=false
ISSUER_CAPABILITY_IS_LIVE_ISSUANCE=false
LIVE_AUTHORIZATION_ISSUED=false
FINAL_MEASURED_ABC_EXECUTION_AUTHORIZED=false
NEW_EXECUTION_AUTHORIZED=false
```

The existing single-use governance invariant remains binding. Runtime anti-replay is not
claimed. Multiple observed executions for one transaction invalidate acceptance.

Historical `authorization_reusable=True` semantics remain prohibited.

## Issuer qualification boundary

The next issuer tranche must bind this exact static record, frozen manifest identity, and
custody receipt.

Issuer qualification itself may not issue live authority or perform the governed execution.

After issuer qualification, fresh platform readiness and fresh human authority remain
required before the single governed execution boundary.

## Safety

This tranche performs:

```text
MODEL_REQUESTS_PERFORMED=0
GPU_EXECUTION_PERFORMED=false
KAGGLE_EXECUTION_PERFORMED=false
NETWORK_TRANSPORT_PERFORMED=false
EFFECT_CLAIMS_PERMITTED=false
```

## Next gate

`QUALIFY_FINAL_342_SINGLE_USE_LIVE_ISSUER_V1`
