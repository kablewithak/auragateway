# ADR: Inventory Full A/B/C Execution-Manifest Assets Before Reconciliation

**ADR ID:** `ADR-LOCAL-ABC-FULL-ABC-EXECUTION-MANIFEST-ASSET-INVENTORY`  
**Date:** 2026-07-18  
**Status:** Accepted  
**Source merge:** `14cc94c74d6a093492732b8123977bd69e1e8ac7`

## Context

PR #95 implemented the local A/B/C integration boundary: canonical condition adapters, one hardened
scoring bridge, one evidence-derived cleanup bridge, a privacy-safe trace envelope, and a fail-closed
comparison preflight.

The repository already contains a Gate 9 planning-ready execution-manifest draft and substantial frozen
benchmark evidence. However, that draft was created before the traceability hardening and the PR #94 and
PR #95 A/B/C integration work. Treating it as current would hide lineage drift.

The next engineering question is not whether the benchmark has any assets. It is which exact assets are
already frozen, which are present but not bound, which are stale, which must be generated during freeze,
and which require external or operator action.

## Decision

Add a typed, canonical asset inventory with six explicit states:

```text
frozen_bound
present_unbound
present_stale
generated_at_freeze
external_blocked
missing_required
```

The inventory binds 44 required assets across governance, corpus and retrieval, context and schemas,
evaluation, telemetry and provider readiness, freeze controls, and execution lineage.

The inventory concludes:

```text
total_assets=44
frozen_bound=28
present_unbound=5
present_stale=4
generated_at_freeze=4
external_blocked=2
missing_required=1
unresolved_required=16
readiness=inventoried_not_ready
```

The repository is not missing its core benchmark constitution. Corpus, retrieval, episodes, quality,
telemetry fixtures, pricing, negative controls, fault fixtures, privacy evidence, and the hardened A/B/C
integration are already present.

The critical gaps are:

1. the Gate 9 draft, ledger, dependency identity, and manifest lineage predate PRs #93 through #95;
2. `condition_configuration_fingerprints` are not yet materialized;
3. pricing, controls, faults, privacy, and the PR #95 source are present but not bound into a reconciled
   draft;
4. `provider_readiness_record` still requires a separately authorized bounded live probe;
5. the cost ceiling requires explicit operator approval; and
6. isolation, final manifest, freeze report, and Gate 10 manifest are freeze-generated outputs.

## Why inventory precedes freeze

Freezing the existing Gate 9 draft would produce an internally valid artifact with stale implementation
lineage. That would make later A/B/C traces claim hardened instrumentation without proving that the frozen
manifest actually bound it.

The inventory therefore blocks direct transition to Gate 10. It advances only to:

```text
full_abc_execution_manifest_draft_reconciliation
```

That next local-only slice must rebuild the draft and run ledger around the PR #95 integration contract,
resolve concrete condition fingerprints, bind present static assets, and expose an exact dependency-lock
source.

## Alternatives rejected

### Freeze the current Gate 9 draft immediately

Rejected because its implementation commit and trace requirements predate the merged hardening and A/B/C
integration.

### Rebuild every benchmark asset

Rejected because 28 required assets are already frozen and hash-addressable. Re-authoring them would add
risk, invalidate prior gates, and create unnecessary future-change cost.

### Treat provider readiness and budget approval as ordinary local files

Rejected because provider readiness requires a bounded live call and budget approval is an operator
control. Both must remain visibly external to local static reconciliation.

### Generate final freeze artifacts during inventory

Rejected because inventory is descriptive and fail-closed. It does not perform a provider call, approve a
budget, freeze a manifest, or issue execution authority.

## Consequences

### Positive

- The next slice operates on concrete gaps rather than a vague readiness claim.
- Frozen research assets remain unchanged.
- Stale Gate 9 lineage cannot silently enter Gate 10.
- Provider and operator blockers remain explicit.
- Final freeze outputs are not fabricated before their prerequisites exist.
- The inventory is machine-readable, hashable, and regression-tested.

### Negative

- Gate 9 must be reconciled even though its original planning checks passed.
- A dependency-lock artifact must be made queryable rather than represented only by a digest.
- Provider readiness and budget approval remain future blockers after local reconciliation.
- Another bounded PR is required before any freeze command can be considered.

## Execution posture

```text
inventory_complete=true
execution_manifest_frozen=false
measured_execution_authorized=false
provider_execution_authorized=false
gpu_execution_authorized=false
provider_call_performed=false
model_request_performed=false
gpu_execution_performed=false
new_authorization_issued=false
consumed_authorization_reused=false
customer_data_used=false
external_spend=0
```

## Next gate

```text
full_abc_execution_manifest_draft_reconciliation
```
