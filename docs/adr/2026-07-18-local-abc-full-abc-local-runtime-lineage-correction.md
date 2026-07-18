# ADR: Supersede hosted-provider lineage in the local A/B/C preflight

- Status: accepted
- Date: 2026-07-18
- Decision ID: `auragateway-full-abc-local-runtime-lineage-correction-v1`
- Source merge: `eb86611670f6163a91343e76d79ff94f8fbfd88c`

## Context

PR #97 produced a current-looking `preflight-v2` planning lineage for the full A/B/C benchmark. The lineage correctly preserved the 342-trajectory schedule, hardened scoring fields, cleanup fields, and zero execution authority. It also incorrectly inherited hosted-provider fields from the legacy Gate 9 draft:

- Groq as the provider/model boundary;
- the Groq adapter in every condition fingerprint;
- a Groq pricing schedule;
- a hosted-provider readiness probe;
- a paid cost-budget approval gate; and
- the `groq` package as a required full-benchmark runtime dependency.

Those fields conflict with the active AuraGateway north star. The intended benchmark is a zero-spend, two-worker local vLLM experiment on Kaggle T4 x2 using the already qualified Qwen model and runtime identity.

The error is lineage contamination, not a request to switch the project to Groq.

## Decision

The merged `preflight-v2` lineage is superseded and classified as non-authoritative, non-executable, and non-comparison-eligible.

The historical files remain unchanged. A new supersession overlay records why they may not be reused.

The authoritative runtime direction is restored to:

```text
execution_backend=local_vllm
environment=kaggle_t4_x2
model=Qwen/Qwen2.5-0.5B-Instruct
model_revision=7ae557604adf67be50417f59c2c2f167def9a775
worker_1=gpu0:8001
worker_2=gpu1:8002
hosted_provider_required=false
provider_credentials_required=false
pricing_in_scope=false
paid_fallback_permitted=false
external_spend=0
```

The exact model, tokenizer, Torch, CUDA, vLLM, wheel, GPU, and worker identities are bound from prior qualified local evidence. This correction does not claim that the current full 342-trajectory runtime is already qualified. A fresh full-run environment review remains required before freeze or execution.

## Consequences

### Positive

- Groq and OpenRouter cannot silently re-enter the local A/B/C execution path.
- The paid cost-budget gate is removed from the north-star path.
- Prior model/runtime evidence is reused as lineage evidence rather than re-invented.
- The invalid PR #97 artifacts remain queryable and auditable.
- Downstream work must rebuild a clean `preflight-v3` lineage.

### Negative

- The PR #97 condition fingerprints, draft, ledger bindings, report, and manifest cannot be reused.
- The 342-trajectory ledger must be regenerated against corrected local-runtime fingerprints.
- The project loses one planning slice of forward progress, but avoids executing the wrong experiment.

## Rejected alternatives

### Continue with the Groq readiness review

Rejected. It advances a hosted-provider experiment that is outside the active north star.

### Replace Groq with another hosted provider

Rejected. The defect is the hosted-provider direction itself, not the specific vendor.

### Delete the PR #97 artifacts

Rejected. Deletion would weaken auditability. The supersession overlay preserves the failure and blocks reuse.

### Treat the model/runtime as unselected

Rejected. Repository evidence already pins the Qwen model, revision, tokenizer, vLLM wheel, Torch/CUDA versions, two T4 GPUs, and worker topology.

## Next gate

`full_abc_local_preflight_v3_rebuild_review`

That gate may design the corrected local-only preflight rebuild. It must not execute a model, start a notebook, enable GPUs, access credentials, or authorize the measured benchmark.
