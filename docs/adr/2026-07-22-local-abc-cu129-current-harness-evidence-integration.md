# ADR: Integrate the current CUDA 12.9 harness only after consumed metadata inspection

- **Status:** Accepted
- **Date:** 2026-07-22
- **Source harness commit:** `426f57dd11dddc2fb8e5a703721c2189abc7a0ff`
- **Decision:** `CURRENT_CU129_HARNESS_EVIDENCE_INTEGRATED`
- **Authorization source policy:** `CONTROL_PACKAGE_AUTHORIZATION_PARITY`

## Context

The active launcher and offline manifest still bound the historical `be1bfadd` harness. The complete
current harness was subsequently packaged from merged main, recovered from Kaggle's auto-expanded ZIP
representation, materialized, and independently inspected with Accelerator None, Internet Off, and no
secrets.

The successful inspection proved exact parity across the materializer receipt, materializer log,
inspection log, five-file inspection evidence bundle, current CUDA 12.9 wheelhouse metadata, and the
unchanged model snapshot.

## Decision

Consume the immutable evidence and migrate the active harness boundary to:

```text
source commit: 426f57dd11dddc2fb8e5a703721c2189abc7a0ff
mounted path: /kaggle/input/notebooks/kabomolefe/ag-harness-materializer-cu129-v1/ag_harness_materializer_cu129_v1_output/auragateway_qualification_harness_426f57d_v1
directory SHA-256: c3ea4ae6d047a8b3f3d5afc517e26c4f13fb4a82e48e3cf28cdfabdc343230e6
file count: 1299
total bytes: 11632357
```

Update the active manifest, materialization record, launcher generator, generated launcher notebook,
and runbook as one propagation boundary.

The launcher must not hard-code the future fresh-authorization merge commit. The control materializer
reads the authorization source commit from the typed authorization payload, writes it into the control
manifest, and the launcher requires exact parity between those two consumed files. This is the
`CONTROL_PACKAGE_AUTHORIZATION_PARITY` policy.

## Evidence

```text
materializer saved version: 337034643
inspection saved version: 337035826
materialization receipt SHA-256: 07d81dbea5b5ed24d0786c0ee16782129e163834254c095262944baaf5c59db2
inspection evidence ZIP SHA-256: 2d2f6afdd53787f6b3977e799dff441f9023a3c265ddf65d35855c5b62ad90d8
operational input closure: PASSED
runtime package count: 176
active manifest SHA-256: f7289cee9414d03d88ceb4775198e15ff9446fd99771a58c187de0d4264ef94a
materialization record SHA-256: 284b488dece09e6b17dcf72e4dea69bbdadd440356ce353622b100c38a02100a
runtime adapter SHA-256: aec461dcd595bfa3af286d88832ec7ef1ca2b416adca6a548f102d9543fb8dba
launcher source SHA-256: 7c0f7f1d466fd68a56d6b77c6e16cf69343491710052818743327b51f1d57f16
launcher notebook SHA-256: 7ec60fd0a162f50961f8ff66a6e3dec3c68a15617109fdc7530b2ec380294de9
```

## Consequences

The historical harness remains preserved as evidence but is no longer active. The historical
authorization issuance implementation remains unusable because its manifest, materialization, adapter,
and source-authority identities predate this integration. A separate implementation boundary must bind
the post-integration merge commit and issue one short-lived authorization only after explicit operator
confirmation.

## Non-claims

This ADR does not claim authorization issuance, GPU execution, package installation, model loading,
worker startup, environment qualification, measured A/B/C authorization, or production readiness.
