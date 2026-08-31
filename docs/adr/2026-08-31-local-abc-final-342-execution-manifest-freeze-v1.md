# ADR: Final-342 Execution Manifest Freeze V1

Date: 2026-08-31

## Status

Proposed for acceptance as the frozen manifest **subject**. Repository-level freeze promotion remains
pending a separate post-commit custody receipt.

## Context

PR #332 completed the final offline end-to-end integration rehearsal. The accepted final 342-run
plan, execution producer, protected-review successor, measured-quality reducer, and analysis engine
now compose through their real typed boundaries without model, GPU, Kaggle, network, or live
authorization work.

The next gate is execution-manifest requalification and freeze. This gate has one unusual identity
constraint that was already resolved by G11.3A: the manifest cannot contain the Git SHA of the same
commit whose tree first contains those manifest bytes. Such a self-reference is recursive.

G11.3A therefore requires two acyclic identities:

1. `source_subject_commit`: the accepted predecessor repository state from which manifest bytes are
   deterministically materialized; and
2. `first_containing_commit`: the first later Git commit whose tree contains those exact bytes.

The second identity is bound by a separate post-commit custody receipt. The repository freeze gate
may not be promoted before that receipt exists and validates.

## Decision

Materialize `FINAL_342_EXECUTION_MANIFEST_V1` from source subject
`fcf403a1c31e26a2cdf3f682a8878db01338a13d`.

This tranche freezes the deterministic manifest subject while keeping repository-level
`EXECUTION_MANIFEST_FROZEN` false until post-commit custody is complete.

### Manifest identity

The manifest carries:

- version `1.0.0`;
- a semantic SHA-256 calculated over canonical manifest content with the
  `execution_manifest_hash` field omitted;
- a separate file SHA-256 exposed by validation for later custody binding;
- Benchmark Constitution 1.0.0 identity;
- final execution producer identity;
- final evidence-bundle schema version;
- exact runtime CPython `cp312` ABI and dependency-lock identity;
- all 69 fields required by Execution Manifest Requirements 1.1.0.

The semantic hash deliberately does not attempt to hash a file containing its own file hash. The
later custody receipt binds both semantic SHA-256 and exact file SHA-256.

### Stable experiment assets

Accepted corpus, retrieval, context, evaluation, fault/privacy, and frozen-control identities are
carried forward from their accepted upstream lineage. The materializer binds the exact accepted
source files by Git blob identity and validates the accepted requirements, G10 denominator,
planned-run ledger, review schedule, and final offline-rehearsal boundary before reconstructing the
manifest.

No experiment content, schedule, denominator, quality threshold, runtime endpoint, bootstrap rule,
or effect-claim rule is regenerated in this tranche.

### Final local runtime specialization

Historical manifest field names were designed around hosted providers. G11.3A and G11.3B explicitly
required those fields to be specialized to the accepted local-vLLM subject rather than silently
reusing historical Groq/Ollama semantics.

The final mapping is:

- `primary_provider = local_vllm`;
- `provider_model_alias = local-qwen2.5-0.5b-instruct`;
- exact model repository and revision are bound directly;
- `provider_adapter_version` names the final loopback-vLLM transport contract;
- the provider-documentation date field is explicitly marked
  `NOT_APPLICABLE_LOCAL_RUNTIME_ARTIFACT_BOUND`;
- telemetry rules bind the final typed turn-measurement contract;
- the exact runtime dependency lock is SHA-256 bound;
- `python_version` binds the CPython 3.12 / `cp312` runtime ABI rather than inventing an
  unobserved patch release.

Fresh platform facts such as the currently observed Kaggle interpreter patch remain platform
readiness evidence after issuer qualification; they are not guessed into static manifest identity.

### Monetary cost scope

G11.3B already closed monetary cost comparison as out of scope:

```text
MONETARY_COST_COMPARISON_IN_SCOPE=false
MONETARY_COST_EFFECT_CLAIMS_PERMITTED=false
MAXIMUM_EXTERNAL_SPEND=0
```

The historical pricing fields remain present because the requirements inventory contains them, but
they are explicitly resolved as not applicable. No local per-request price, pricing date, or
currency is fabricated.

### Route-policy specialization

The final experiment uses one local model under two worker-routing schedules:

- turn-local: `worker_1, worker_2, worker_1, worker_2`;
- affinity: `worker_1, worker_1, worker_1, worker_1`.

Historical economy/capable model aliases therefore both map to the same local model alias. The
treatment difference is the frozen worker route, not a model-class choice.

The legacy `capability_calibration_report_hash` field is specialized to the canonical SHA-256 of an
embedded local route-compatibility resolution. This prevents reuse of a historical hosted-model
calibration artifact under misleading semantics.

### Protected review schedule

The manifest binds the final protected deterministic secondary-review schedule SHA-256:

`9566edb218c2d9c6459e8428bc93676bc1e73484b2fd56a249aed2cc1db6748c`

This supersedes using the historical public review-schedule asset hash as final measured-review
identity.

### Runtime identity

The manifest binds the accepted exact runtime:

- environment: `kaggle_t4_x2`;
- backend: `local_vllm`;
- Python ABI: `cp312`;
- model: `Qwen/Qwen2.5-0.5B-Instruct`;
- model revision: `7ae557604adf67be50417f59c2c2f167def9a775`;
- vLLM: `0.25.1+cu129`;
- Torch: `2.11.0+cu129`;
- Torch CUDA: `12.9`;
- Triton: `3.6.0`;
- Transformers: `5.14.1`;
- GPU: `Tesla T4`, compute capability `7.5`;
- attention backend: `TRITON_ATTN`;
- transport endpoint: `/v1/chat/completions`;
- exact runtime requirements lock:
  `cf5d773ef5c26f2e42a7afd76f0e466c21847169986f14fe5a7ac9ad02f0a3c3`.

These values are configuration identity. Fresh platform readiness remains a later observation.

## Freeze semantics

This tranche establishes:

```text
MANIFEST_SUBJECT_BYTES_FROZEN=true
POST_COMMIT_CUSTODY_RECEIPT_REQUIRED=true
REPOSITORY_EXECUTION_MANIFEST_FROZEN=false
REPOSITORY_FREEZE_GATE_PROMOTED=false
FINAL_MEASURED_ABC_EXECUTION_AUTHORIZED=false
NEW_EXECUTION_AUTHORIZED=false
EFFECT_CLAIMS_PERMITTED=false
MODEL_REQUESTS_PERFORMED=0
GPU_EXECUTION_PERFORMED=false
KAGGLE_EXECUTION_PERFORMED=false
NETWORK_TRANSPORT_PERFORMED=false
LIVE_AUTHORIZATION_ISSUED=false
```

The distinction between frozen subject bytes and repository freeze promotion is intentional.

## Change prohibition

Once the manifest subject is committed, any byte change creates a new manifest subject and
invalidates the pending custody transition. The later custody receipt must bind the exact semantic
and file SHA-256 values produced by this tranche and the exact first commit containing those bytes.

No later authority may silently rewrite a manifest-controlled field.

## Rejected alternatives

### Embed the first-containing Git commit in this manifest

Rejected because it creates recursive Git identity.

### Reuse the historical Groq execution manifest

Rejected because the final runtime is local vLLM with one Qwen model and worker-route treatments.
Historical provider/model-routing semantics are immutable lineage, not final configuration.

### Invent local monetary pricing fields

Rejected because monetary cost comparison is explicitly out of scope and external spend is zero.

### Freeze an unobserved Python patch version

Rejected because the exact runtime evidence freezes the CPython `cp312` ABI, not a durable Kaggle
patch release. Fresh platform facts are checked later rather than guessed now.

### Use the historical public review-schedule hash

Rejected because the final measured-review successor explicitly requires the protected deterministic
schedule SHA-256 to be bound by the final manifest.

## Next gate

`BIND_FINAL_342_EXECUTION_MANIFEST_POST_COMMIT_CUSTODY_V1`
