# Full A/B/C Local Runtime Lineage Correction v1

## Decision

The `preflight-v2` artifacts merged in PR #97 are invalid for future planning, execution, comparison eligibility, and claim generation because they imported Groq provider, adapter, pricing, readiness, and budget fields from a legacy hosted-provider draft.

This correction restores the active benchmark direction without changing historical artifacts.

## Superseded lineage

```text
source_merge_commit=d6531fdc0b27892dcc299598f9f251fa157434dc
manifest_path=data/evals/benchmark/preflight-v2/manifest.json
manifest_git_blob_sha=2ed78faefbfa8cf8a464c8cc96349b808dd5c855
status=superseded_invalid_non_executable
reason=HOSTED_PROVIDER_LINEAGE_IMPORTED_INTO_LOCAL_BENCHMARK
```

The following PR #97 outputs are invalidated as one lineage:

```text
dependency_lock_sha256=44c69022985216f88fff5186a563724d8cb9b715577d47bfe1629a8ea19edd88
condition_fingerprints_sha256=6af3b45b8495ad41ef93b71db156305b78f9b72bf0de0ce04637f013c09ef6d0
input_sha256=fcfec50011e9851c9b904aa8155076997967057ef977ad53c28b59f1e570a0f7
execution_manifest_sha256=ae0a70c4c0a00ebc5b11dad757b6f101d756e39d7d563b21d5a973dea451f9d9
plan_sha256=cf22d4dbb78a7b9bd9d77c90a1d2b5b20ebf1f27102ca919562d5ffd81f2c16a
report_sha256=1681a1964c6857e3824b0c834057dd8a3f84d886dfbe8206a189bdc1a1ace351
spec_sha256=e7bd972fe11f055b21fe66ae1d5deb362db37ad35b7c593327ef103afbda5678
```

## Invalidated fields

The correction explicitly blocks:

```text
dependency_lock.packages.groq
condition provider_model_alias=groq-gpt-oss-20b
condition provider_adapter_version=groq-chat-completions-v1
condition pricing_schedule_id=groq-openai-gpt-oss-20b-ondemand-2026-07-13
execution-manifest Groq provider and pricing fields
provider readiness as a hosted external blocker
paid cost-budget approval as an external blocker
the provider-readiness and budget-review next gate
```

## Restored local runtime identity

```text
execution_backend=local_vllm
environment=kaggle_t4_x2
transport_endpoint=/v1/chat/completions
worker_client_contract=auragateway.local_abc.worker_client.WorkerClient
worker_registry_contract=auragateway.local_abc.worker_registry.WorkerRegistry
```

### Model

```text
model_alias=local-qwen2.5-0.5b-instruct
repository=Qwen/Qwen2.5-0.5B-Instruct
revision=7ae557604adf67be50417f59c2c2f167def9a775
model_manifest_sha256=b5c53c05aa258cf85b8ac7c1f41ec81aaa6d9d66a656d32f7271bf5d4c9b8daa
config_sha256=18e18afcaccafade98daf13a54092927904649e1dd4eba8299ab717d5d94ff45
generation_config_sha256=e558847a8b4402616f1273797b015104dc266fe4b520056fca88823ba8f8ebe6
tokenizer_json_sha256=c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539
tokenizer_config_sha256=5b5d4f65d0acd3b2d56a35b56d374a36cbc1c8fa5cf3b3febbbfabf22f359583
```

### Runtime

```text
gpu_count=2
gpu_model=Tesla T4
compute_capability=7.5
torch_version=2.11.0+cu129
torch_cuda_version=12.9
vllm_module_version=0.25.1
vllm_distribution_version=0.25.1+cu129
vllm_wheel_sha256=9e206f370c934a2d4b6b1f05d3d09708d344e05d80260189ef19f60755709431
worker_1=gpu0:8001
worker_2=gpu1:8002
```

## Supporting evidence

```text
measured_execution_authorization_v1
  role=two_worker_environment
  canonical_sha256=64565dd6d34d7d9f9e55a4522b594ef95c458b0ff1af7994dfe81b39a8ba4e74

reconcile_balance_extraction_requalification_authorization_v2
  role=model_runtime_authorization
  canonical_sha256=a2a35e3fb566ed697089dd41c962c7d932490eaeda3ab12f1f3955c285225899

reconcile_balance_extraction_requalification_evidence_audit_v2
  role=successful_model_execution_audit
  canonical_sha256=a6a1031d85997d8b13b521866d580ce468579cfbb8d731180820fdcc5dd0be79

reconcile_balance_extraction_requalification_authorization_consumption_v2
  role=authorization_consumption
  canonical_sha256=51b36a3ac4e6122c2cf9fa9e5132d26e57af101a19714cb4cd60c4c71afdff4f
```

## Safety state

```text
preflight_v2_planning_authoritative=false
preflight_v2_execution_eligible=false
preflight_v2_comparison_eligible=false
groq_in_full_abc_scope=false
openrouter_in_full_abc_scope=false
hosted_provider_probe_required=false
cost_budget_required=false
pricing_schedule_required=false
model_execution_performed=false
provider_call_performed=false
gpu_execution_performed=false
credential_accessed=false
measured_execution_authorized=false
claim_generation_permitted=false
external_spend=0
```

## Important limit

Historical evidence proves the exact local model/runtime lineage and prior bounded execution. It does not prove that the current hardened 342-trajectory full benchmark environment is ready. Current full-run environment requalification remains required.

## Next gate

`full_abc_local_preflight_v3_rebuild_review`

The next gate must rebuild the local-only dependency identity, condition fingerprints, execution-manifest draft, planned ledger, report, and manifest. It may not reuse the invalid PR #97 fingerprints or authorize execution.
