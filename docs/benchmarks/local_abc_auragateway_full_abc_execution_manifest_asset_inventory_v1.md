# AuraGateway Full A/B/C Execution-Manifest Asset Inventory v1

**Version:** 1.0.0  
**Date:** 2026-07-18  
**Status:** Inventory complete; execution manifest not ready or authorized

## Source authority

```text
source_merge_commit=14cc94c74d6a093492732b8123977bd69e1e8ac7
integration_source_blob_sha=269cfd38cbe789d35ca44a8006d9c29f9558a6a0
implementation_plan_blob_sha=4a6dfea4b90cebad4052ca5eadf09a4bdc2520f7
implementation_plan_sha256=758da13f236fcbe38df68240edc9eb7fefc49f8b26ca480fcea0a826978fc662
integration_design_sha256=5ee5bc868652a456c60c9a388b634537866117344b4a5b3f12130ddbc1a5c9c1
benchmark_constitution_sha256=c58074be896de122d82b063905aed34f67e8f37446a31581391e26d956c9fcc1
inventory_sha256=900b3b80a051d1af716154f67a7a2b3d964df653fd23abca107c321af84440d6
```

## Inventory decision

```text
readiness=inventoried_not_ready
inventory_complete=true
execution_manifest_frozen=false
measured_execution_authorized=false
```

The repository already contains the core benchmark evidence. The next work is targeted reconciliation,
not rebuilding the project from scratch.

## State summary

| State | Count | Meaning |
|---|---:|---|
| `frozen_bound` | 28 | Existing immutable asset with a content or Git identity |
| `present_unbound` | 5 | Existing asset that must be inserted into the reconciled draft |
| `present_stale` | 4 | Existing lineage that predates the hardened A/B/C integration |
| `generated_at_freeze` | 4 | Output that may exist only after all freeze prerequisites pass |
| `external_blocked` | 2 | Requires a provider call or explicit operator approval |
| `missing_required` | 1 | Required local artifact that does not yet exist |
| **Total** | **44** | Exact required inventory |

```text
unresolved_required_count=16
local_gap_count=14
external_gap_count=2
```

## Frozen and reusable foundations

### Governance and integration

```text
benchmark_constitution
execution_manifest_requirements
integration_design
integration_implementation
```

The integration assets preserve:

- the A/B/C causal contrasts;
- one shared hardened scorer;
- one shared cleanup classifier;
- required prompt and cleanup trace fields;
- privacy-safe trace envelopes;
- fail-closed comparison eligibility.

### Corpus and retrieval

```text
corpus_manifest
chunking_manifest
retrieval_freeze_manifest
retrieval_development_manifest
heldout_retrieval_cases
heldout_retrieval_scorecard
```

The selected configuration remains:

```text
retrieval_implementation=dense-hashed-tfidf-section-aware-remediated-v2
chunking_strategy=section-aware-v1
top_k=5
metadata_policy=authored-case-filters-v1
retrieval_configuration_fingerprint=220ce9ac6e19789bedf1aedc2b6253db5ba03a09ebcc6efdac203eb80cd23490
```

### Context and schemas

```text
static_anchor_registry
static_compiler_spec
prefix_determinism_manifest
prompt_policy
response_schema
action_schema
```

Gate 3 already proves canonical static serialization, HMAC prefix fingerprinting, stable-turn behavior,
and mutation sensitivity. The action-extraction prompt, response schema, and deterministic action contract
remain common across A, B, and C.

### Evaluation and evidence

```text
diagnostic_episode_manifest
functional_episode_set
runtime_episode_selection
blinded_review_protocol
quality_rubric
review_assignment_schedule
deterministic_quality_manifest
quality_noninferiority_manifest
feedback_evidence_manifest
comparison_eligibility_manifest
```

The fixed episode constitution remains:

```text
functional_episodes=18
development_episodes=12
held_out_episodes=6
runtime_episodes=6
turns_per_episode=4
```

### Telemetry and provider calibration

```text
telemetry_fixture_manifest
provider_calibration_manifest
```

These prove deterministic normalization, sufficiency behavior, provider error taxonomy, and adapter
calibration. They do not replace bounded live provider readiness.

## Present but unbound static assets

The following files exist and have exact SHA-256 identities, but Gate 9 still leaves their final manifest
fields unset:

```text
integration_source
pricing_schedule
negative_control_manifest
fault_injection_fixture_set
privacy_verification_report
```

Required action:

```text
bind all five into the reconciled execution-manifest draft
```

The existing pricing schedule is versioned and remains an estimate, not an invoice. It must be bound before
cost-budget calculation.

## Stale lineage

```text
dependency_lock_identity
execution_manifest_draft
gate9_preflight_manifest
planned_run_ledger
```

These artifacts are not rejected as structurally invalid. They are stale because they predate:

- explicit executed-prompt identity propagation;
- evidence-derived cleanup classification;
- the full A/B/C integration design;
- the local adapter, scoring, cleanup, trace, and preflight implementation.

The existing Gate 9 draft references an older implementation commit and does not bind current
condition-configuration fingerprints or hardened trace fields.

## Missing local artifact

```text
condition_configuration_fingerprints
```

Target path:

```text
data/evals/benchmark/preflight-v2/condition_fingerprints.json
```

The next slice must derive one canonical fingerprint for each condition from the PR #95 adapters. These
fingerprints must differ only where the frozen causal design permits differences.

## External blockers

### Provider readiness

```text
asset_id=provider_readiness_record
state=external_blocked
provider_call_required=true
```

Target path:

```text
data/evals/benchmark/freeze-v1/provider_readiness.json
```

This requires a separately authorized bounded live provider probe. The inventory performs no provider call
and does not reuse an earlier authorization.

### Cost-budget approval

```text
asset_id=cost_budget_approval
state=external_blocked
operator_approval_required=true
```

The worst-case estimate is deterministic, but the approved USD ceiling must be explicitly supplied by the
operator before freeze.

## Freeze-generated artifacts

These are not missing implementation files and must not be fabricated during inventory:

```text
cross_condition_isolation_report
final_execution_manifest
freeze_report
gate10_manifest
```

They are generated only after the reconciled Gate 9 evidence, provider readiness, and approved budget pass.

## Blocker set

```text
condition_configuration_fingerprints
cost_budget_approval
cross_condition_isolation_report
dependency_lock_identity
execution_manifest_draft
fault_injection_fixture_set
final_execution_manifest
freeze_report
gate10_manifest
gate9_preflight_manifest
integration_source
negative_control_manifest
planned_run_ledger
pricing_schedule
privacy_verification_report
provider_readiness_record
```

## Required next slice

```text
full_abc_execution_manifest_draft_reconciliation
```

That slice must be local-only and must:

1. generate canonical A/B/C configuration fingerprints;
2. establish a concrete dependency-lock artifact and digest;
3. rebuild the execution-manifest draft against PR #95;
4. bind the integration design, implementation plan, and source blob;
5. bind pricing, negative controls, fault fixtures, and privacy verification;
6. regenerate the 342-trajectory run ledger with hardened trace requirements;
7. produce a new planning preflight manifest and report;
8. preserve `execution_enabled=false`; and
9. perform no model, provider, notebook, or GPU execution.

## Safety boundary

```text
provider_call_performed=false
model_request_performed=false
gpu_execution_performed=false
execution_manifest_frozen=false
measured_execution_authorized=false
provider_execution_authorized=false
gpu_execution_authorized=false
new_authorization_issued=false
consumed_authorization_reused=false
customer_data_used=false
external_spend=0
```

## Non-claims

- This inventory does not freeze an execution manifest.
- This inventory does not claim Gate 9 is current after PR #95.
- This inventory does not perform a provider readiness probe.
- This inventory does not approve a cost budget.
- This inventory does not create Gate 10 evidence.
- This inventory does not authorize measured execution or comparative claims.
- This inventory does not establish provider cache usage, latency savings, or cost savings.
- This inventory does not establish production readiness.
