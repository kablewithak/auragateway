# AuraGateway P5/P6 Mechanism-Admission Successor Execution Authorization Issuer V1

## Purpose

Implement the control-plane bridge between the merged mechanism-admission successor and one future governed execution.

The bridge has two deterministic parts: a single-use authorization issuer and a successor-specific materializer for the exact three-file Kaggle control package already required by the runtime consumer.

## Bound successor

- merge commit: `2b1841aee4397ae0c72bad6b2c9e7069835d8399`
- scope: `P5_P6_MECHANISM_ADMISSION_SUCCESSOR_V1`
- runtime-script SHA-256: `a63d395ec3caa2f7a13723679b0bf081ba11d4246cf2b8e87ea644d3bcecd958`
- implementation-review SHA-256: `3a5eebca0bb53439309456b19464fb7b0a707e6c0274e3fae2144fa9ccb35330`
- design-record SHA-256: `6137052bd06503bbb77589d043a095fb3a8d2e8ae4d6d56e75296d34b8c6310c`
- mechanism-admission contract SHA-256: `95948be1f9487dbfc650efd11b4789a4f3c60302c7cc9e38e2e1c271076684d8`
- runtime-outcome addendum SHA-256: `395f9c7e9955594d7c962659dd882e0851dcc6f9833715bb53e5d37bb7439239`

## Controls

The issuer requires fresh T4 x2/internet-off platform evidence, explicit operator confirmation, synchronized clean `main`, exact successor artifact identities, bounded execution resources, a non-overwriting live authorization path, and terminal non-reusability.

The transport materializer produces the successor-specific `GOVERNED_ROOT_EXACT_FLAT_V1` package. Its generated notebook is CPU-only and does not execute during repository implementation.

## Implementation posture

```text
LIVE_AUTHORIZATION_ISSUED=false
RUNTIME_EXECUTION_AUTHORIZED=false
MODEL_REQUESTS_PERFORMED=0
GPU_EXECUTION_PERFORMED=false
KAGGLE_EXECUTION_PERFORMED=false
```

## Acceptance boundary

Repository acceptance requires canonical generated review/record bytes, focused tests covering freshness, scope rejection, issuer-to-transport compatibility, non-overwriting single use, terminalization, exact-flat materialization, and CPU-only notebook generation.

This tranche does not requalify P5 or P6 and does not authorize the variance pilot or final A/B/C run.
