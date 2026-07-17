# Local A/B/C Reconcile-Balance Action-Extraction Authorization Review v2

## Decision

```text
review_id=reconcile-balance-action-extraction-authorization-review-v2
status=review_ready_inactive
decision=approved_for_separate_activation
source_merge_commit=bb732bf88020cb031f534bb0b67d74b8f8f05483
active_authorization_created=false
model_request_performed=false
gpu_execution_authorized=false
```

The versioned remediation is sufficiently bounded and materially different to justify a separate
activation review. This artifact does not activate or execute it.

## Frozen identities

```text
parent_evidence_audit_sha256=8e0294686db03adab55e3341914417bb0dfd630e97adc6fe36a9d671d36744bd
remediation_manifest_sha256=82037903ab9d944a88e6d1460a001a648308163ed7dae735cbf01359737ae4aa
remediation_plan_sha256=ebeb86b583eeff4f8b2c3ea973f67d6aaba1368a4386eb53737179ed3fd64a36
normalization_policy_sha256=7caa66d8bba36260fb97f822fdeea4f4badc16b1add1b5ed9eb5896be6257ef8
prompt_policy_sha256=750a6f89c7ada7b9d508eaf143214e3d93e6456bb4b3586afa7dc089f8dcfc4c
response_schema_sha256=bb81d7bbb98524b748cb91eb3cc0f4083f8d7df430016caa42724396af72687d
action_schema_sha256=923c7fb8c5abadf80c65e55516330e7ec48bd5147ec24662a8cc5dbeed0b76a7
```

Merged PR #86 source bindings:

```text
action_extraction_remediation.py blob=379dddb3efcf53eb1f57b909a16e9ed0b8226619
remediation_cases_v2.json blob=6a3cb9b677b9c4ccaa1e4f55e57325a0e535511e
remediation_plan_v2.json blob=b0b82a3cded9e8e64103e6813c8da240dd127176
```

## Baseline and promotion gate

```text
baseline_cases=12
baseline_exact_operands=10/12
baseline_exact_final_answers=10/12
reviewed_cases=16
required_exact_operands=16/16
required_exact_final_answers=16/16
complete_suite_required=true
```

The entire suite must run once. The two failed historical cases cannot be run in isolation.

## Materially different intervention

```text
raw synthetic source
    ↓
deterministic integer lexical normalization
    ↓
semantic role-bound v2 instruction
    ↓
role-described JSON Schema
    ↓
strict unchanged ReconcileBalanceAction validation
    ↓
unchanged deterministic arithmetic executor
```

The intervention addresses:

```text
FORMATTED_INTEGER_LEADING_COMPONENT_DROPPED
KEY_VALUE_CREDIT_DEBIT_ROLE_REVERSAL
```

No model upgrade, retry, repair, replacement, or deterministic semantic-parser fallback is added.

## Metadata-only dry run

The dry run contains 16 ordered attempt records. Each record retains:

- sequence index;
- evaluation case ID;
- source-prompt SHA-256;
- normalized-prompt SHA-256;
- rendered-prompt SHA-256;
- expected action SHA-256;
- expected deterministic answer.

It contains no raw prompts and permits no model request.

## Proposed runtime boundary

The later activation may reuse only the previously qualified identity:

```text
model=Qwen/Qwen2.5-0.5B-Instruct
revision=7ae557604adf67be50417f59c2c2f167def9a775
runtime=vLLM 0.25.1 / distribution 0.25.1+cu129
torch=2.11.0+cu129
cuda=12.9
gpu=dual Tesla T4
worker=worker_1
request_attempts_per_case=1
```

Any drift must fail activation or notebook preflight.

## Proposed evidence boundary

Evidence may retain hashes, normalization counts, typed scores, timings, token counts, failure
codes, and worker lifecycle records. It may not retain raw prompts, raw outputs, raw actions, token
IDs, credentials, PII, or customer data.

## Artifact fingerprints

```text
authorization_review_sha256=66539ccadbebee9ad6227b8d861da8bfa1f0e89fdd69883e91f49b15819c99a9
authorization_dry_run_sha256=207abb6746277b1f6bc4ca79d537de3623f06d66ca5fa8600ee391af45acf508
authorization_review_manifest_sha256=8299da7aaba1ed886d5bf85b9ee59c2471e79f735b1f37d66b9b8c3c806eee2d
```

## Current safety state

```text
prior_authorization_consumed=true
prior_authorization_reuse_permitted=false
provider_call_performed=false
model_request_performed=false
credential_accessed=false
active_authorization_created=false
execution_command_available=false
notebook_generation_permitted=false
execution_authorized=false
gpu_execution_authorized=false
cache_claims_permitted=false
full_measured_rerun_authorized=false
```

## Next gate

```text
bounded_action_extraction_v2_authorization_activation
```

The activation must be a separate bounded PR. It may create a new one-shot authorization and permit
later notebook generation, but it must not execute a model or authorize the full A/B/C benchmark.

## Non-claims

This review does not claim:

- measured improvement over the 10/12 baseline;
- that the two semantic failures are fixed in model execution;
- that the future canary will pass;
- cache reuse, latency, or cost improvement;
- full A/B/C comparison eligibility;
- production readiness.
