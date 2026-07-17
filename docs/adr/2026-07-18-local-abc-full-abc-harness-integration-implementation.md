# ADR: Implement the Hardened Full A/B/C Harness Integration Boundary

**ADR ID:** `ADR-LOCAL-ABC-FULL-ABC-HARNESS-INTEGRATION-IMPLEMENTATION`  
**Date:** 2026-07-18  
**Status:** Accepted  
**Source merge:** `430fe12445dce4563274b880f203da175acb567d`

## Context

PR #94 froze how the future full A/B/C harness must consume the action-extraction traceability and
cleanup hardening from PR #93. The design requires all three conditions to use one scorer, one cleanup
classifier, one prompt and schema boundary, and one privacy-safe trace shape.

A design-only artifact is insufficient. The next risk is implementation drift: separate condition code
could silently reconstruct prompt identities, weaken cleanup semantics, omit required trace fields, or
allow comparisons before the execution manifest and authorization gates are satisfied.

The execution manifest is not frozen. Measured, provider, and GPU execution are not authorized.

## Decision

Implement a local-only integration module with five explicit boundaries:

1. a canonical A/B/C condition-adapter builder;
2. a shared action-extraction scoring bridge using the hardened v2 scorer;
3. a shared evidence-derived cleanup bridge;
4. a typed privacy-safe trace envelope carrying every frozen design field; and
5. a fail-closed comparison-eligibility preflight.

The preflight separates quality and runtime eligibility:

- `CLEAN` may support both quality and runtime comparison when every other gate passes;
- `CLEAN_WITH_RUNTIME_WARNINGS` may preserve quality evidence but blocks runtime comparison;
- `FAILED` blocks both metric families.

Poor model quality is retained as an outcome and is not treated as an exclusion reason. The preflight
checks evidence structure, lineage, cleanup, namespace isolation, manifest bindings, and execution
authority. It does not generate claims and does not authorize reruns.

## Alternatives rejected

### Build three independent condition runners

Rejected because condition-specific scorer or cleanup code would create an instrumentation confound and
could recreate the defects closed by PR #93.

### Treat warning-qualified cleanup as fully clean

Rejected because forced termination or resource leakage can distort runtime evidence even when completed
quality evidence remains usable.

### Exclude failed model outputs before comparison

Rejected because poor quality is a measured result, not an exclusion reason. Failure-accounted
denominators must remain intact.

### Freeze or authorize the execution manifest in this slice

Rejected because the required execution assets and fingerprints have not yet been inventoried and bound.
This implementation does not authorize provider, model, GPU, notebook, or measured execution.

## Consequences

### Positive

- Every condition consumes the same hardened scoring and cleanup functions.
- Prompt-policy and rendered-prompt identities become first-class trace fields.
- Cleanup warnings cannot silently enter runtime comparisons.
- Cross-condition cache namespace collisions are blocked before reporting.
- Missing manifest, configuration, or authority bindings fail closed.
- Public traces exclude raw prompts, outputs, provider payloads, credentials, and personal identifiers.

### Negative

- Future execution-manifest work must provide condition-specific expected configuration fingerprints.
- Runtime eligibility is stricter than quality evidence retention.
- Provider-cache claims remain blocked until telemetry sufficiency is implemented and proven.
- Another asset-inventory and manifest-freeze boundary is required before authorization review.

## Execution posture

```text
execution_manifest_frozen=false
measured_execution_authorized=false
provider_execution_authorized=false
gpu_execution_authorized=false
new_authorization_issued=false
consumed_authorization_reused=false
model_request_performed=false
provider_call_performed=false
gpu_execution_performed=false
customer_data_used=false
external_spend=0
```

This implementation does not authorize execution or comparative claims.

## Next gate

```text
full_abc_execution_manifest_asset_inventory
```
