# AuraGateway Full A/B/C Local Preflight-v3 Rebuild v1

## Status

```text
implementation=complete
planning_assets=generated_locally_after_install
execution_enabled=false
execution_manifest_frozen=false
measured_execution_authorized=false
lifecycle=LOCALLY_VALIDATED
external_spend=0
next_gate=full_abc_local_full_run_environment_qualification_review
```

## Purpose

This slice implements the clean planning lineage approved by PR #99. It replaces the invalid
hosted-provider-contaminated `preflight-v2` planning bindings without deleting historical evidence.

It does not qualify or execute the benchmark.

## Generated artifacts

| Artifact | Purpose | Authority after generation |
|---|---|---|
| `developer_dependency_lock.json` | Exact local validation environment | Planning only |
| `condition_fingerprints.json` | Clean A/B/C configuration identities | Planning only |
| `input.json` | Source identities and frozen episode sets | Planning only |
| `execution_manifest_draft.json` | Unfrozen local execution plan | Non-executable |
| `planned_run_ledger.json` | Complete 342-trajectory plan | Not started |
| `preflight_report.json` | Gate result and outstanding blockers | Execution blocked |
| `manifest.json` | Hash inventory for the six non-self artifacts | Planning lineage complete |

## A/B/C invariants

```text
A:
  prefix_policy=cache_hostile
  route_schedule=worker_1,worker_2

B:
  prefix_policy=deterministic_exact
  route_schedule=worker_1,worker_2

C:
  prefix_policy=deterministic_exact
  route_schedule=worker_1,worker_1
```

Required relationships:

```text
A.route_schedule == B.route_schedule
B.prefix_token_hash == C.prefix_token_hash
A.prefix_token_hash != B.prefix_token_hash
all shared configuration fields equal across A, B, C
```

## Dependency result

The local developer lock records exact installed versions. It does not serve as the future Kaggle
runtime lock.

Expected AuraGateway development evidence at this boundary includes:

```text
python=3.12.10
ruff=0.15.21
pydantic=2.13.4
mypy=1.20.2
pytest=9.1.1
groq=1.5.0 historical_only
setuptools=resolved_from_active_environment
```

The generated artifact is authoritative for the actual resolved versions.

## Ledger result

```text
functional_episode_count=18
functional_replications=3
functional_trajectories=162
runtime_episode_count=6
runtime_replications=10
runtime_trajectories=180
total_trajectories=342
turns_per_trajectory=4
total_turns=1368
maximum_request_attempts=2736
```

All run IDs, trace IDs, cache namespaces, and order indexes are unique. Every run remains
`not_started`.

## Explicit blockers

```text
cache_diagnostics=blocked_for_later_gate
environment_qualification=blocked_for_later_gate
variance_pilot=blocked_for_later_gate
execution_freeze=blocked_for_later_gate
```

The implementation does not reinterpret historical action-extraction evidence as current full-run
qualification.

## Privacy and safety

```text
customer_data_used=false
raw_prompts_retained=false
raw_documents_retained=false
raw_model_outputs_retained=false
credentials_accessed=false
provider_call_performed=false
notebook_execution_performed=false
gpu_execution_performed=false
external_spend=0
```

## Validation contract

Required validation order:

```text
1. Generate canonical preflight-v3 files.
2. Verify byte-for-byte deterministic regeneration.
3. Run focused unit tests.
4. Run all local_abc tests.
5. Run the complete pytest suite.
6. Run Ruff 0.15.21 lint.
7. Run the safe format check with historical exclusions.
8. Run strict mypy.
9. Run git diff --check.
10. Stage exact files and verify scope.
```

## Non-claims

This slice does not prove:

- current Kaggle T4 x2 availability;
- current vLLM installation compatibility;
- current two-worker health;
- cache reuse or isolation;
- reset correctness;
- pressure or eviction behaviour;
- fault recovery;
- variance adequacy;
- quality non-inferiority;
- any A/B/C effect;
- measured-execution eligibility; or
- production readiness.
