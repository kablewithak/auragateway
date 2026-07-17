# AuraGateway Full A/B/C Execution-Manifest Draft Reconciliation v2

**Version:** 2.0.0  
**Date:** 2026-07-18  
**Status:** Local draft current; execution unauthorized

## Source authority

```text
source_merge_commit=d6531fdc0b27892dcc299598f9f251fa157434dc
integration_design_sha256=5ee5bc868652a456c60c9a388b634537866117344b4a5b3f12130ddbc1a5c9c1
integration_implementation_sha256=758da13f236fcbe38df68240edc9eb7fefc49f8b26ca480fcea0a826978fc662
asset_inventory_sha256=900b3b80a051d1af716154f67a7a2b3d964df653fd23abca107c321af84440d6
benchmark_constitution_sha256=c58074be896de122d82b063905aed34f67e8f37446a31581391e26d956c9fcc1
reconciliation_spec_sha256=e7bd972fe11f055b21fe66ae1d5deb362db37ad35b7c593327ef103afbda5678
```

## Purpose

This boundary replaces the stale Gate 9 planning lineage with a current local preflight-v2 lineage. It
makes the manifest draft, dependency identity, condition fingerprints, and 342-trajectory ledger current
without authorizing provider or measured execution.

## Generated artifacts

```text
data/evals/benchmark/preflight-v2/dependency_lock.json
data/evals/benchmark/preflight-v2/condition_fingerprints.json
data/evals/benchmark/preflight-v2/input.json
data/evals/benchmark/preflight-v2/execution_manifest_draft.json
data/evals/benchmark/preflight-v2/planned_run_ledger.json
data/evals/benchmark/preflight-v2/preflight_report.json
data/evals/benchmark/preflight-v2/manifest.json
```

The artifacts are generated locally because the dependency lock must bind exact versions from the active
validated virtual environment.

## Exact dependency lock

The lock captures:

```text
project=auragateway
project_version=from pyproject.toml
python_implementation=CPython
python_version=exact active interpreter
groq=exact installed version
pydantic=exact installed version
mypy=exact installed version
pytest=exact installed version
ruff=exact installed version
setuptools=exact installed version
```

Missing packages block generation with `DEPENDENCY_DISTRIBUTION_NOT_FOUND`.

## A/B/C fingerprints

The generator materializes the exact PR #95 adapters and builds one fingerprint for each condition:

```text
A = cache-hostile context + turn-local route
B = deterministic context + turn-local route
C = deterministic context + cache-affinity/TTL route
```

All three fingerprints bind the same:

```text
dependency lock
integration design and implementation
Benchmark Constitution
retrieval configuration
v2 prompt policy
response schema
action schema
provider/model alias
provider adapter
pricing schedule
benchmark runner version
```

The fingerprints must be distinct because the condition adapters differ only on the frozen causal
variables.

## Reconciled planned ledger

```text
functional_schedule=functional-counterbalance-v1
runtime_schedule=runtime-counterbalance-v1
functional_trajectories=162
runtime_trajectories=180
total_trajectories=342
total_turns=1368
maximum_request_attempts=2736
```

Every run contains:

```text
schedule_index
run_id
comparison_pair_id
workload
episode_id
replication_id
condition_id
benchmark_condition_id
condition_order_index
cache_namespace_id
configuration_fingerprint
turn_count
maximum_request_attempt_count
```

Run IDs and cache namespaces are unique. The runtime episodes remain a six-case subset of the 18-case
functional set.

## Current draft bindings

The v2 draft binds:

```text
PR #96 source commit
exact local dependency lock
A/B/C condition-fingerprint manifest
integration design
integration implementation
asset inventory
Benchmark Constitution
corpus and retrieval identities
episode identities
quality rubric and review schedule
Gate 7 feedback evidence
Gate 8 comparison eligibility
telemetry fixture identity
pricing schedule
negative controls
fault fixtures
privacy verification
hardened trace-field set
```

The draft does not pretend that freeze-time evidence exists.

## Remaining blockers

```text
provider_readiness_record
cost_budget_approval
cross_condition_isolation_report
final_execution_manifest
freeze_report
gate10_manifest
```

Provider readiness and budget approval are external decisions. Isolation and Gate 10 outputs are generated
only after those decisions pass.

## Reconciliation decision

```text
source_commit_current=passed
dependency_lock_resolved=passed
condition_fingerprints_resolved=passed
integration_lineage_current=passed
static_assets_bound=passed
planned_ledger_current=passed
trace_fields_current=passed
execution_disabled=passed
provider_readiness_pending=blocked_external
cost_approval_pending=blocked_external
freeze_outputs_pending=pending_freeze
```

## Safety and privacy

```text
model_request_performed=false
provider_call_performed=false
gpu_execution_performed=false
credential_accessed=false
customer_data_used=false
execution_enabled=false
measured_execution_permitted=false
claim_generation_permitted=false
external_spend=0
```

The generated lineage contains identifiers, hashes, versions, controls, and planned-run metadata. It does
not contain raw prompts, raw outputs, retrieved document text, provider payloads, credentials, secrets, or
personal information.

## Reproducibility

Generation and verification use the same deterministic builder. Verification reconstructs every artifact
and requires byte-for-byte equality.

```text
python -m auragateway.local_abc.full_abc_execution_manifest_draft_reconciliation generate
python -m auragateway.local_abc.full_abc_execution_manifest_draft_reconciliation verify
```

## Validation

```text
focused_reconciliation_tests=17 passed
all_local_abc_tests=635 passed
ruff_version=0.15.21
ruff_check=passed
ruff_format_check=passed
strict_mypy=passed
python_compilation=passed
canonical_json=passed
```

The user's complete repository checkout is authoritative for the complete test suite.

## Next gate

```text
full_abc_provider_readiness_and_budget_review
```

## Non-claims

- This boundary does not freeze Gate 10.
- This boundary does not perform a provider probe.
- This boundary does not approve a cost ceiling.
- This boundary does not authorize measured execution.
- This boundary does not claim provider cache usage.
- This boundary does not claim latency, cache, quality, or cost results.
