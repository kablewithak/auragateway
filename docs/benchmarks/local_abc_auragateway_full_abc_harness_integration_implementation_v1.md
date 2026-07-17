# AuraGateway Full A/B/C Harness Integration Implementation v1

**Version:** 1.0.0  
**Date:** 2026-07-18  
**Status:** Locally implemented; execution and claims unauthorized

## Source authority

```text
source_merge_commit=430fe12445dce4563274b880f203da175acb567d
design_blob_sha=5d1bcb3a4fd26096d2e0d5f8c51e38ef927de0d3
integration_design_sha256=5ee5bc868652a456c60c9a388b634537866117344b4a5b3f12130ddbc1a5c9c1
hardening_source_blob_sha=d991beb28a70e90a2de6fb805dba53ca5cf16d33
implementation_plan_sha256=758da13f236fcbe38df68240edc9eb7fefc49f8b26ca480fcea0a826978fc662
```

## Implemented boundaries

```text
condition_adapter_builder=
auragateway.local_abc.full_abc_harness_integration.
build_full_abc_condition_runtime_adapters

scoring_bridge=
auragateway.local_abc.full_abc_harness_integration.
score_full_abc_action_extraction

cleanup_bridge=
auragateway.local_abc.full_abc_harness_integration.
classify_full_abc_worker_cleanup

trace_builder=
auragateway.local_abc.full_abc_harness_integration.
build_full_abc_trace_envelope

comparison_preflight=
auragateway.local_abc.full_abc_harness_integration.
evaluate_full_abc_comparison_preflight
```

## Condition adapters

The adapter set materializes exactly one adapter for A, B, and C in canonical order.

```text
A: cache_hostile + turn_local + boundary_not_enforced
B: deterministic_exact + turn_local + boundary_enforced
C: deterministic_exact + cache_affinity_ttl + boundary_enforced
```

Every adapter binds the same:

```text
prompt_policy_sha256=750a6f89c7ada7b9d508eaf143214e3d93e6456bb4b3586afa7dc089f8dcfc4c
response_schema_sha256=bb81d7bbb98524b748cb91eb3cc0f4083f8d7df430016caa42724396af72687d
action_schema_sha256=923c7fb8c5abadf80c65e55516330e7ec48bd5147ec24662a8cc5dbeed0b76a7
```

Condition-specific scoring and cleanup semantics remain prohibited.

## Shared scoring bridge

The scoring bridge accepts already-retained output text and performs local evaluation only.

```text
retained output
    -> evaluate_reconcile_balance_extraction_v2
    -> ActionExtractionCaseScore
    -> score_prompt_policy_sha256
    -> score_rendered_prompt_sha256
```

It performs no model request and retains no raw prompt or raw output in its evidence contract.

A failed score remains a failed measured outcome. It is not silently repaired, retried, or removed from
future quality denominators.

## Shared cleanup bridge

The cleanup bridge delegates to the evidence-derived three-state classifier:

```text
CLEAN
CLEAN_WITH_RUNTIME_WARNINGS
FAILED
```

Metric-family handling is explicit:

| Cleanup state | Quality evidence | Runtime comparison |
|---|---|---|
| `CLEAN` | Eligible when all other gates pass | Eligible when all other gates pass |
| `CLEAN_WITH_RUNTIME_WARNINGS` | May remain eligible | Blocked |
| `FAILED` | Blocked | Blocked |

This distinction prevents forced termination or resource leakage from being hidden inside runtime claims
while preserving complete task-quality evidence where defensible.

## Typed trace envelope

The trace envelope carries every field frozen by the integration design:

```text
run_id
trace_id
comparison_pair_id
episode_id
replication_id
condition_id
cache_namespace_id
session_id_hash
provider_model_alias
benchmark_manifest_hash
execution_manifest_hash
configuration_fingerprint
score_prompt_policy_sha256
score_rendered_prompt_sha256
cleanup_status
cleanup_warning_codes
```

The envelope also enforces the public privacy boundary:

```text
raw_prompt_retained=false
raw_user_message_retained=false
raw_conversation_history_retained=false
raw_retrieved_document_text_retained=false
raw_model_output_retained=false
raw_provider_payload_retained=false
credentials_retained=false
secrets_retained=false
direct_personal_identifiers_retained=false
```

## Comparison preflight

The preflight evaluates one frozen causal contrast and checks:

- exact condition order for A/B, B/C, or A/C;
- shared comparison-pair, episode, and replication identity;
- provider/model alias parity;
- benchmark- and execution-manifest parity;
- expected condition configuration fingerprints;
- distinct cross-condition cache namespaces;
- active v2 score prompt-policy identity;
- cleanup state;
- execution-manifest freeze state; and
- measured, provider, and GPU authorization state.

The preflight returns separate booleans for quality and runtime metric eligibility. It always keeps:

```text
provider_cache_claim_eligible=false
claim_generation_permitted=false
rerun_authorized=false
original_records_retained=true
```

Provider-cache claims remain blocked because telemetry-sufficiency integration is outside this slice.

## Failure taxonomy

```text
DESIGN_FINGERPRINT_MISMATCH
EXECUTION_MANIFEST_UNFROZEN
MEASURED_EXECUTION_UNAUTHORIZED
PROVIDER_EXECUTION_UNAUTHORIZED
GPU_EXECUTION_UNAUTHORIZED
CONDITION_PAIR_MISMATCH
COMPARISON_PAIR_ID_MISMATCH
EPISODE_ID_MISMATCH
REPLICATION_ID_MISMATCH
PROVIDER_MODEL_ALIAS_MISMATCH
BENCHMARK_MANIFEST_MISMATCH
EXECUTION_MANIFEST_MISMATCH
CONFIGURATION_FINGERPRINT_MISMATCH
CACHE_NAMESPACE_COLLISION
PROMPT_POLICY_MISMATCH
CLEANUP_FAILED
CLEANUP_WARNING_BLOCKS_RUNTIME
```

## Validation

```text
focused_implementation_tests=25 passed
ruff_version=0.15.21
ruff_check=passed
ruff_format_check=passed
strict_mypy=passed
python_compilation=passed
canonical_json=passed
```

## Execution and safety boundary

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

This implementation does not authorize execution, provider-cache claims, measured A/B/C results, or
production-readiness claims.

## Next gate

```text
full_abc_execution_manifest_asset_inventory
```

The next slice must inventory and hash-bind the concrete corpus, retrieval, prompt, schema, rubric,
condition-configuration, telemetry, schedule, pricing, dependency, and implementation assets required for
an execution manifest. It must still perform no model, provider, notebook, or GPU execution.

## Non-claims

- This slice does not freeze the execution manifest.
- This slice does not issue or reuse an authorization.
- This slice does not execute a model, provider request, notebook, or GPU workload.
- This slice does not establish provider cache usage.
- This slice does not claim latency, cost, or cache savings.
- This slice does not produce measured A/B/C results.
- This slice does not establish production readiness.
