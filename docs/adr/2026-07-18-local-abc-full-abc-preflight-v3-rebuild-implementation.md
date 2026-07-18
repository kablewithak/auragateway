# ADR: Implement the clean local-only full A/B/C preflight-v3 planning lineage

- Status: accepted
- Date: 2026-07-18
- Decision ID: `auragateway-full-abc-local-preflight-v3-rebuild-v1`
- Source main merge: `3c9894d9b176329e4442aaedb4d93e88715ce38f`
- Review authority: `auragateway-full-abc-local-preflight-v3-rebuild-review-v1`

## Context

PR #99 accepted the boundary for rebuilding AuraGateway's full A/B/C planning lineage after
PR #98 invalidated the hosted-provider-contaminated `preflight-v2` artifacts.

The accepted review permits generation of local planning assets only. It does not permit:

- Kaggle or GPU activity;
- model requests;
- credentials;
- provider calls;
- measured execution authorization;
- execution-manifest freeze; or
- causal claims.

The implementation must preserve the frozen 342-trajectory benchmark shape while removing Groq,
OpenRouter, provider readiness, pricing, currency, and cost-budget fields from the active lineage.

## Decision

Implement a typed generator at:

```text
src/auragateway/local_abc/full_abc_local_preflight_v3_rebuild.py
```

The generator produces seven canonical JSON files under:

```text
data/evals/benchmark/preflight-v3/
```

Generated files:

```text
developer_dependency_lock.json
condition_fingerprints.json
input.json
execution_manifest_draft.json
planned_run_ledger.json
preflight_report.json
manifest.json
```

The generator has two CLI operations:

```powershell
python -m auragateway.local_abc.full_abc_local_preflight_v3_rebuild generate `
    --repo-root .

python -m auragateway.local_abc.full_abc_local_preflight_v3_rebuild verify `
    --repo-root .
```

`generate` builds, writes, and verifies the planning lineage. `verify` regenerates the expected
models in memory and compares them byte-for-byte with the committed JSON files.

## Dependency boundary

The implementation creates a developer validation lock from the active virtual environment and
`pyproject.toml`.

The developer lock records:

- `pydantic` as the active local contract runtime;
- `mypy`, `pytest`, and `ruff` as development dependencies;
- `setuptools` as a build dependency; and
- `groq` as a historical hosted-provider dependency that is not active for the full A/B/C runtime.

The Kaggle runtime dependency lock is not generated in this gate. Its values remain
`UNRESOLVED_BEFORE_ENVIRONMENT_QUALIFICATION` until a fresh T4 x2 environment is reviewed and
qualified.

## Condition fingerprints

The implementation generates exactly three configuration fingerprints in A, B, C order.

Machine-enforced invariants:

```text
A.route_schedule == B.route_schedule
B.prefix_token_hash == C.prefix_token_hash
A.prefix_token_hash != B.prefix_token_hash
A.shared_configuration == B.shared_configuration == C.shared_configuration
```

The fingerprint payloads contain no provider adapter, provider readiness, pricing, currency, or
budget fields.

The legacy trace field `provider_model_alias` remains only in a separate compatibility boundary.
Its value is fixed to `local-qwen2.5-0.5b-instruct`, and it carries no provider authority.

The prefix hash stored at this stage is a planning identity. Runtime token identity must still be
confirmed during fresh environment and cache-observability qualification.

## Planned run ledger

The implementation regenerates the complete benchmark ledger from the frozen functional episode
set and runtime selection.

```text
functional_trajectories=162
runtime_trajectories=180
total_trajectories=342
total_turns=1368
maximum_request_attempts=2736
```

Each run receives deterministic identifiers, a UUID5 trace identifier, a unique cache namespace,
the clean v3 condition fingerprint, and a planning-manifest identity.

Every entry begins with:

```text
attempt_number=1
terminal_classification=not_started
```

No run is executed. The ledger prohibits hidden retries, replacement cases, and reuse of
`preflight-v2` hash bindings.

## Execution-manifest draft

The generated draft is planning-complete but remains:

```text
execution_enabled=false
execution_manifest_frozen=false
provider_execution_authorized=false
gpu_execution_authorized=false
measured_execution_authorized=false
claim_generation_permitted=false
external_spend=0
```

The draft retains the exact local Qwen, vLLM, Torch, CUDA, worker, and wheel direction as historical
lineage evidence. It explicitly requires fresh full-run environment requalification.

The following assets remain unresolved after this gate:

```text
cache-observability-qualification
cache-pressure-diagnostics
cache-reset-qualification
current-environment-report
execution-manifest-freeze
fault-diagnostics
kaggle-runtime-dependency-lock
measured-execution-authorization
repetition-count-freeze
variance-pilot
worker-isolation-qualification
```

## Failure handling

The generator fails closed for:

- missing or invalid source assets;
- source identity drift;
- missing PR #99 ancestry;
- an invalid or unapproved PR #99 review;
- incomplete PR #98 supersession controls;
- missing local validation packages;
- non-CPython execution;
- condition invariant drift;
- episode-set drift;
- ledger count or identity collisions;
- provider or pricing contamination; and
- byte-level generated artifact drift.

Failures use metadata-safe error envelopes. Raw prompts, documents, model outputs, provider
payloads, credentials, and personal data are never written by this gate.

## Consequences

### Positive

- The active planning lineage is local-only and zero-spend.
- The contaminated `preflight-v2` hashes are not reused.
- The 342-run ledger is regenerated against clean condition fingerprints.
- Dependency and runtime boundaries are separated correctly.
- Planning artifacts are deterministic and independently verifiable.
- Later qualification requirements remain visible rather than being silently treated as complete.

### Negative

- The generated developer lock is environment-specific and must be regenerated from the user's
  validated virtual environment.
- The legacy `provider_model_alias` trace field remains technical debt until a separate migration.
- The implementation does not advance the lifecycle beyond `LOCALLY_VALIDATED`.
- Current Kaggle, cache, pressure, fault, and variance evidence remains absent.

## Rejected alternatives

### Reuse the `preflight-v2` ledger and replace only provider names

Rejected. The v2 condition fingerprints and hash bindings are explicitly superseded and cannot be
made trustworthy through string substitution.

### Generate the Kaggle runtime lock from historical values

Rejected. Historical values establish direction, not current full-run qualification.

### Remove `provider_model_alias` in this slice

Rejected. That would be an unrelated trace-contract migration with a larger regression surface.

### Freeze or authorize execution after generation

Rejected. Planning completeness is not environment qualification, comparison eligibility, or
execution authority.

## Next gate

```text
full_abc_local_full_run_environment_qualification_review
```

That review may define the exact fresh Kaggle T4 x2 qualification package and stop conditions. It
must not execute a notebook, enable a GPU, start workers, install the vLLM wheel, or invoke a model.
