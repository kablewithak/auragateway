# ADR: Define the clean local-only full A/B/C preflight-v3 rebuild boundary

- Status: accepted
- Date: 2026-07-18
- Decision ID: `auragateway-full-abc-local-preflight-v3-rebuild-review-v1`
- Source main merge: `f3e625518fb61af7c1a8197ef51ba5b38bcae510`
- Review fingerprint: `8d06fba955ffb6266d23fd02d716d052fcfa21955520eb9cce73ae695bec8ccb`

## Context

PR #98 restored AuraGateway's active completion path to a zero-spend, two-worker local vLLM
benchmark on Kaggle T4 x2. It also made PR #97's hosted-provider-contaminated preflight-v2
lineage non-authoritative, non-executable, and non-comparison-eligible.

The next boundary is not execution. It is a review that defines how a clean preflight-v3 lineage
will be rebuilt without importing:

- Groq or OpenRouter runtime authority;
- hosted-provider readiness probes;
- pricing schedules, currencies, or paid budgets;
- preflight-v2 condition fingerprints;
- preflight-v2 execution-manifest hashes; or
- preflight-v2 planned-ledger bindings.

The repository already contains valid assets that should be preserved:

- PR #95's shared A/B/C integration implementation;
- PR #96's 44-asset inventory as an artifact census;
- PR #98's exact local runtime correction and supersession;
- the frozen Benchmark Constitution; and
- the Execution Manifest Requirements.

The review must also resolve a naming debt. `FullABCTraceEnvelope` currently exposes
`provider_model_alias`, even though the active runtime is local. Renaming it inside this slice would
expand the change into a trace-contract migration and increase regression risk.

## Decision

Create a typed, canonical review artifact that approves only a bounded preflight-v3 rebuild
implementation.

The review makes these decisions.

### 1. Carry forward only valid authorities

Carry forward:

- PR #95 integration implementation;
- PR #96 asset inventory, with provider and budget blockers reinterpreted locally;
- PR #98 local runtime correction;
- Benchmark Constitution;
- Execution Manifest Requirements; and
- the local extension PRD as a hash-bound local design authority without promoting the PRD file to
  Git.

Bind the PR #98 preflight-v2 supersession as a fail-closed guardrail. It is not a reusable execution
input.

### 2. Separate dependency locks

Preflight-v3 will use two distinct dependency artifacts:

```text
data/evals/benchmark/preflight-v3/developer_dependency_lock.json
data/evals/benchmark/preflight-v3/kaggle_runtime_dependency_lock.json
```

The developer lock records the repository validation environment and may retain installed historical
packages such as `groq`, but must mark them inactive for the full local A/B/C runtime.

The Kaggle runtime lock is created only during fresh environment qualification and must capture the
exact Python, CUDA, Torch, vLLM, Transformers, model, tokenizer, cache, worker-startup, and GPU
configuration. Unresolved values remain `UNRESOLVED_BEFORE_ENVIRONMENT_QUALIFICATION`.

### 3. Define local-only condition fingerprints

All three condition fingerprints share the exact model, tokenizer, runtime, scorer, retrieval,
quality, metric-mapping, and execution-requirement identities.

Condition-specific fields are limited to:

```text
condition_id
prefix_policy
route_schedule
cache_namespace_id
prefix_token_hash
```

The causal invariants remain:

```text
B.prefix_token_hash == C.prefix_token_hash
A.route_schedule == B.route_schedule
all shared fingerprint fields are equal across A, B, and C
```

Provider-adapter, provider-readiness, pricing, currency, and budget fields are prohibited.

### 4. Retain the legacy trace field without provider authority

`provider_model_alias` remains in the trace envelope for compatibility. During the local benchmark it
must equal:

```text
local-qwen2.5-0.5b-instruct
```

Its semantics are explicitly:

```text
legacy_name_bound_to_local_runtime_model_alias_without_provider_authority
```

Any rename requires a separate contract migration with trace fixtures and regression tests.

### 5. Regenerate the full ledger

The clean v3 planned ledger must be regenerated against v3 fingerprints.

```text
functional_trajectories=162
runtime_trajectories=180
total_trajectories=342
total_turns=1368
maximum_request_attempts=2736
```

The ledger preserves counterbalanced orders, one bounded retry per turn, every attempted run, and
explicit terminal classification. Hidden retries, case replacement, and v2 hash reuse are forbidden.

### 6. Preserve unresolved gates

The review records unresolved assets across five legal stages:

```text
preflight_v3_rebuild
environment_qualification
diagnostic_qualification
variance_pilot
execution_freeze
```

The review does not collapse historical feasibility evidence into current full-run qualification.

### 7. Keep execution disabled

The review fixes all execution and claim flags to false and external spend to zero.

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
hosted_provider_required=false
pricing_in_scope=false
external_spend=0
claim_generation_permitted=false
```

## Consequences

### Positive

- The clean v3 implementation has a deterministic contract before code generation begins.
- Hosted-provider and pricing contamination fail closed.
- Developer validation dependencies are separated from governed Kaggle runtime dependencies.
- The 342-trajectory ledger can be rebuilt without changing the causal constitution.
- The existing trace contract remains stable while its local semantics become explicit.
- Historical evidence remains queryable without becoming current authorization.

### Negative

- The review adds no measured progress and intentionally leaves the lifecycle at
  `LOCALLY_VALIDATED`.
- A later implementation slice must generate the v3 planning artifacts.
- Fresh Kaggle qualification is still required before runtime values can be frozen.
- The legacy trace-field name remains technical debt until a separately reviewed migration.

## Rejected alternatives

### Extend the PR #97 preflight-v2 generator

Rejected. The v2 generator's input and output bindings are contaminated by hosted-provider lineage.
A clean namespace is cheaper to reason about and safer to audit.

### Remove `provider_model_alias` immediately

Rejected. The field is embedded in the PR #95 trace contract and comparison preflight. Renaming it
inside the lineage review would mix contract migration with execution planning.

### Treat the installed `groq` package as an active runtime dependency

Rejected. Repository history may require the package, but the active full A/B/C execution path does
not.

### Generate v3 artifacts in the review slice

Rejected. Review and implementation are separate gates. Generating assets before the schema is
accepted would repeat the planning error that PR #98 corrected.

## Next gate

`full_abc_local_preflight_v3_rebuild_implementation`

That gate may implement and generate the local-only developer lock, v3 condition fingerprints,
input, planned ledger, execution-manifest draft, preflight report, and manifest. It must keep
execution disabled and must not start Kaggle, enable GPUs, invoke a model, access credentials, or
authorize measured execution.
