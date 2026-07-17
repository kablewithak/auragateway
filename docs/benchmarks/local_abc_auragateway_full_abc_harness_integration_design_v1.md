# AuraGateway Full A/B/C Harness Integration Design v1

**Version:** 1.0.0
**Date:** 2026-07-18
**Status:** Design frozen; implementation and execution unauthorized

## Source authority

```text
source_merge_commit=b995794e1e1f312c23f39a685b3c118253707700
benchmark_constitution_blob_sha=dc25906298a611b71f3482da85c6aba763c474e7
hardening_source_blob_sha=d991beb28a70e90a2de6fb805dba53ca5cf16d33
hardening_plan_blob_sha=449007bd4d0fe55596aee24c313b4ec6b1677ceb
hardening_plan_sha256=aa6a02dee2ceb039e61d13048075a3a0081777538b2c08277d4a381f2b5a47e3
integration_design_sha256=5ee5bc868652a456c60c9a388b634537866117344b4a5b3f12130ddbc1a5c9c1
```

## Integration objective

The future measured A/B/C harness must use the hardened score identity and cleanup semantics in all three
conditions. Instrumentation may not vary by condition.

```text
executed prompt
    -> explicit v2 prompt identity
    -> shared action-extraction scorer
    -> score trace fields

worker terminal evidence
    -> shared cleanup classifier
    -> CLEAN | CLEAN_WITH_RUNTIME_WARNINGS | FAILED
    -> comparison eligibility
```

## Conditions

### Condition A — Cache-Hostile Baseline

```text
prefix_policy=cache_hostile
route_policy=turn_local
static_volatile_boundary_enforced=false
```

Condition A must remain plausible and functional. It may not be deliberately degraded beyond the frozen
context-construction difference.

### Condition B — Prefix-Deterministic Runtime

```text
prefix_policy=deterministic_exact
route_policy=turn_local
static_volatile_boundary_enforced=true
```

A versus B isolates deterministic context construction while holding route behavior fixed.

### Condition C — Cache-Aware Agent Runtime

```text
prefix_policy=deterministic_exact
route_policy=cache_affinity_ttl
static_volatile_boundary_enforced=true
```

B versus C isolates cache-affinity routing while preserving deterministic context construction.

## Shared hardening boundary

Every condition binds:

```text
score_entrypoint=
auragateway.local_abc.action_extraction_traceability_cleanup_hardening.
evaluate_reconcile_balance_extraction_v2

cleanup_entrypoint=
auragateway.local_abc.action_extraction_traceability_cleanup_hardening.
classify_action_extraction_worker_cleanup

prompt_policy_sha256=
750a6f89c7ada7b9d508eaf143214e3d93e6456bb4b3586afa7dc089f8dcfc4c

response_schema_sha256=
bb81d7bbb98524b748cb91eb3cc0f4083f8d7df430016caa42724396af72687d

action_schema_sha256=
923c7fb8c5abadf80c65e55516330e7ec48bd5147ec24662a8cc5dbeed0b76a7
```

Condition-specific scorers or cleanup semantics are prohibited.

## Causal contrasts

| Contrast | Permitted claim | Prohibited attribution |
|---|---|---|
| A versus B | Context-construction policy effect | Cache-affinity routing effect |
| B versus C | Route-policy effect | Context-construction effect |
| A versus C | Total system effect | Attribution to one mechanism |

## Benchmark suites

### Functional suite

```text
episodes=18
turns_per_episode=4
conditions=3
repetitions_per_condition=3
scheduled_trajectories=162
schedule_id=functional-counterbalance-v1
```

### Runtime microbenchmark

```text
episodes=6
turns_per_episode=4
conditions=3
repetitions_per_condition=10
scheduled_trajectories=180
schedule_id=runtime-counterbalance-v1
```

The runtime subset may not replace the full functional quality benchmark.

## Quality non-inferiority gate

```text
policy_id=quality-non-inferiority-v1
max_task_success_regression_percentage_points=5
minimum_structured_output_validity=0.95
citation_support_regression_permitted=false
unsupported_answer_rate_increase_permitted=false
retrieval_configuration_change_permitted=false
unsafe_behavior_regression_permitted=false
comparison_eligibility_required=true
```

A cheaper or faster condition that fails the quality gate is a quality regression, not an improvement.

## Telemetry claim gate

```text
unknown_values_remain_unknown=true
missing_cache_value_coerced_to_zero=false
warm_eligibility_proves_provider_cache_hit=false
provider_cache_claim_requires_observed_provider_evidence=true
cache_latency_cost_claim_requires_sufficiency_decision=true
```

This design does not overturn the terminal Groq or OpenRouter evidence decisions.

## Trace contract

Every future measured trajectory must include the Benchmark Constitution run identity plus:

```text
score_prompt_policy_sha256
score_rendered_prompt_sha256
cleanup_status
cleanup_warning_codes
```

These fields make prompt lineage and shutdown quality queryable before comparison eligibility or claims.

## Privacy boundary

Public evidence excludes raw prompts, user messages, conversation history, retrieved document text, model
outputs, hidden reasoning, provider payloads, credentials, secrets, direct personal identifiers, and
unbounded metadata.

## Execution posture

```text
execution_manifest_frozen=false
measured_execution_authorized=false
gpu_execution_authorized=false
provider_execution_authorized=false
new_authorization_issued=false
consumed_authorization_reused=false
full_abc_results_claimed=false
```

No model request, GPU execution, provider call, or credential access is performed.

## Regression gate

The design tests prove:

- Conditions preserve the frozen A/B/C causal differences;
- all conditions share one hardened scorer and cleanup classifier;
- prompt, response-schema, action-schema, retrieval, and rubric boundaries remain constant;
- causal contrasts cannot claim the wrong mechanism;
- functional and runtime trajectory counts cannot drift;
- missing provider telemetry cannot become zero;
- score identity and cleanup warning trace fields cannot be removed;
- privacy exclusions remain fixed;
- no execution authority is introduced.

## Next gate

```text
full_abc_harness_integration_implementation
```

## Non-claims

- This design does not freeze the execution manifest.
- This design does not reopen any consumed provider or model authorization.
- This design does not claim provider cache usage or savings.
- This design does not produce measured A/B/C results.
- This design does not authorize a notebook or provider request.
- This design does not establish production readiness.
