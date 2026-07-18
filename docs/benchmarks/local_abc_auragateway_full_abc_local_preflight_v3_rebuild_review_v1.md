# AuraGateway Full A/B/C Local Preflight-v3 Rebuild Review v1

## Result

```text
review_id=auragateway-full-abc-local-preflight-v3-rebuild-review-v1
review_sha256=8d06fba955ffb6266d23fd02d716d052fcfa21955520eb9cce73ae695bec8ccb
decision=APPROVED_FOR_BOUNDED_REBUILD_IMPLEMENTATION
lifecycle_before=LOCALLY_VALIDATED
lifecycle_after=LOCALLY_VALIDATED
next_gate=full_abc_local_preflight_v3_rebuild_implementation
```

This review defines the clean local-only preflight-v3 lineage. It performs no model, notebook, GPU,
provider, credential, or measured-execution activity.

## Premises

### Historical

- Groq and OpenRouter evidence are closed and immutable.
- The action-extraction canary and requalification notebooks are consumed evidence.
- PR #97 preflight-v2 is retained for auditability but is not reusable.

### Current

- PR #98 restores local vLLM, Kaggle T4 x2, Qwen 2.5 0.5B, and R0 spend.
- PR #95 integration remains valid.
- PR #96 inventory remains a valid asset census.
- The full 342-trajectory benchmark is not environment-qualified or authorized.

### Planned

- Implement clean preflight-v3 planning assets.
- Perform fresh environment and diagnostic qualification.
- Run a counterbalanced variance pilot.
- Freeze a clean execution manifest.
- Obtain separate measured-execution authorization.

## Authority bindings

| Binding | Identity | Carry forward |
|---|---|---:|
| PR #95 integration source | Git blob `269cfd38cbe789d35ca44a8006d9c29f9558a6a0` | Yes |
| PR #96 asset inventory | SHA-256 `900b3b80a051d1af716154f67a7a2b3d964df653fd23abca107c321af84440d6` | Yes |
| PR #98 runtime correction | SHA-256 `1927239e919741f96b6c8017b241413b42d9528de109db1cd7df7a0dfd9b0fe7` | Yes |
| PR #98 v2 supersession | SHA-256 `df39761f7f6c73787bffacb5e933b4ea4d35f4079e86ff94ec846f63e2ae1cd6` | Guardrail only |
| Benchmark Constitution | SHA-256 `c58074be896de122d82b063905aed34f67e8f37446a31581391e26d956c9fcc1` | Yes |
| Execution Manifest Requirements | SHA-256 `30799246e6fa8d91246a5277e613ed97f840a164331f1f04a3f17fd84aad20cf` | Yes |
| Local extension PRD v1.0.0 | SHA-256 `c7e9a3cde75a0acf06903ed1a3947a757b9c5ec04f2be6374af393a570dac76e` | Design authority |

## Dependency boundary

The review separates repository validation from governed execution.

### Developer dependency lock

```text
path=data/evals/benchmark/preflight-v3/developer_dependency_lock.json
sources=pyproject.toml + installed validation environment
```

Historical packages may be recorded, but hosted-provider packages are not active full-benchmark
runtime dependencies.

### Kaggle runtime dependency lock

```text
path=data/evals/benchmark/preflight-v3/kaggle_runtime_dependency_lock.json
status=UNRESOLVED_BEFORE_ENVIRONMENT_QUALIFICATION
```

Required fields include Python, CUDA, GPU, Torch, vLLM, Transformers, model/tokenizer revisions,
dtype, quantization, attention backend, model length, GPU memory utilization, APC configuration,
output budget, wheel SHA, and worker-startup command SHA.

## Condition fingerprint contract

Shared across A, B, and C:

- execution backend and environment;
- local model and tokenizer identities;
- Torch, CUDA, and vLLM identities;
- worker client and registry contracts;
- scorer prompt, response, and action schema hashes;
- retrieval and quality hashes;
- benchmark and execution-requirement hashes;
- decoding, runtime, and metric-mapping hashes.

Condition-specific:

```text
condition_id
prefix_policy
route_schedule
cache_namespace_id
prefix_token_hash
```

Required invariants:

```text
B.prefix_token_hash == C.prefix_token_hash
A.route_schedule == B.route_schedule
shared_fields(A) == shared_fields(B) == shared_fields(C)
```

## Legacy trace-field decision

The PR #95 trace field `provider_model_alias` remains for compatibility. The local value is fixed to
`local-qwen2.5-0.5b-instruct`. The name conveys no hosted-provider authority. A rename is deferred to
a separate contract migration.

## Ledger regeneration

```text
functional_trajectories=162
runtime_trajectories=180
total_trajectories=342
turns_per_trajectory=4
total_turns=1368
maximum_retries_after_initial_attempt=1
maximum_request_attempts=2736
counterbalanced_orders=A-B-C,B-C-A,C-A-B
```

The v3 ledger must not reuse v2 condition fingerprints, manifest hashes, plan hashes, or report
hashes. Every attempt remains in the ledger. Hidden retry and case replacement remain prohibited.

## Unresolved asset map

### Preflight-v3 rebuild

- developer dependency lock;
- local condition fingerprints;
- planned run ledger.

### Environment qualification

- current environment report;
- Kaggle runtime dependency lock.

### Diagnostic qualification

- cache observability;
- cache reset;
- worker isolation;
- cache pressure;
- fault diagnostics.

### Variance pilot

- counterbalanced pilot;
- repetition-count freeze.

### Execution freeze

- execution-manifest freeze;
- separate measured-execution authorization.

## Safety state

```text
execution_enabled=false
preflight_v3_assets_generated=false
execution_manifest_frozen=false
measured_execution_authorized=false
gpu_execution_authorized=false
model_execution_performed=false
notebook_execution_performed=false
provider_call_performed=false
credential_accessed=false
customer_data_used=false
hosted_provider_required=false
paid_fallback_permitted=false
pricing_in_scope=false
external_spend=0
claim_generation_permitted=false
```

## Validation contract

The source module validates:

- canonical review JSON;
- PR #98 correction and supersession fingerprints;
- PR #96 inventory fingerprint;
- committed Git blob identities for PR #95, PR #96, and PR #98 source files;
- Benchmark Constitution and Execution Manifest Requirements content hashes;
- fail-closed preflight-v2 flags; and
- a privacy-safe summary containing no prompts, outputs, credentials, or customer data.

## Non-claims

This review does not claim:

- current Kaggle availability;
- current two-worker health;
- current cache observability;
- current reset or isolation qualification;
- variance-pilot completion;
- execution-manifest freeze;
- measured-execution authorization;
- any A/B/C effect;
- quality non-inferiority; or
- production readiness.
