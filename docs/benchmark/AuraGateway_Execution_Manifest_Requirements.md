# AuraGateway Execution Manifest Requirements

## Status

```text
Document version: 1.1.0
Constitution dependency: AuraGateway Benchmark Constitution 1.0.0
Execution manifest status: Draft created; not frozen
Benchmark planning status: Deterministic A/B/C ledger implemented
Measured execution permitted: No
```

## Purpose

The frozen Benchmark Constitution defines how AuraGateway evidence must be generated and interpreted.

The execution manifest pins the exact assets and implementation versions used for a measured run. This separation allows Phases 1–6 to create and validate the corpus, retrieval configuration, context compiler, provider adapters, route policy, evaluation assets, fault controls, and comparison-eligibility rules without reopening Gate 0.

The current draft and run ledger are planning artifacts. They do not authorize Groq, Ollama, or any A/B/C provider execution.

## Execution manifest freeze point

The execution manifest may be frozen only after Gates 1–8 have supplied the required validated assets.

No functional A/B/C or runtime microbenchmark execution may begin before that freeze.

The freeze procedure must additionally resolve every field that is explicitly `null` in the current draft, complete a bounded provider live probe, declare a versioned cost ceiling when cost remains in scope, and update the Git commit to the commit containing the frozen manifest.

## Required identity fields

```text
execution_manifest_version
execution_manifest_hash
benchmark_constitution_version
benchmark_constitution_hash
benchmark_runner_version
comparison_eligibility_contract_version
evidence_bundle_schema_version
git_commit_hash
python_version
dependency_lock_hash
```

## Corpus and retrieval fields

```text
corpus_manifest_hash
chunking_strategy_id
chunking_configuration_hash
retrieval_implementation_id
retrieval_configuration_hash
retrieval_type
top_k
metadata_filter_policy_version
development_retrieval_manifest_hash
held_out_retrieval_manifest_hash
retrieval_scorecard_hash
```

These values are supplied after Gate 1.

## Context and contract fields

```text
prompt_template_id
prompt_template_version
static_context_pack_id
static_context_pack_version
serialization_version
tool_contract_version
output_schema_version
prefix_fingerprint_contract_version
```

These values are supplied after Gate 3.

## Provider and telemetry fields

```text
primary_provider
provider_model_alias
exact_model_identifier
provider_adapter_version
provider_documentation_date_checked
telemetry_rules_version
telemetry_fixture_manifest_hash
cache_ttl_assumption_seconds
cache_ttl_source
pricing_schedule_version
pricing_source_date
currency
```

These values are supplied after Gate 4.

A provider or model change after execution-manifest freeze invalidates affected measured comparisons.

## Route-policy fields

```text
route_policy_version
economy_model_alias
capable_model_alias
capability_calibration_report_hash
route_ttl_policy_version
provider_failure_policy_version
```

These values are supplied after Gate 5.

## Evaluation and adjudication fields

```text
diagnostic_episode_manifest_hash
functional_benchmark_manifest_hash
runtime_microbenchmark_manifest_hash
quality_rubric_version
quality_rubric_hash
blinded_adjudication_protocol_version
review_sample_schedule_hash
feedback_evidence_contract_version
```

These values are supplied after Gates 2, 6, and 7.

## Fault and privacy fields

```text
negative_control_manifest_hash
fault_injection_fixture_hash
privacy_trace_contract_version
privacy_verification_report_hash
cross_condition_isolation_test_hash
```

These values are supplied after Gate 8.

## Frozen execution controls

The manifest must repeat and bind the following constitution controls:

```text
functional_run_order_schedule_id
runtime_run_order_schedule_id
timeout_policy_id
retry_policy_id
exclusion_policy_id
rerun_policy_id
denominator_policy_id
statistical_reporting_configuration_id
quality_non_inferiority_policy_id
```

The values must match Constitution 1.0.0.

## Planning ledger

The deterministic planner expands the frozen constitution into:

```text
functional trajectories: 162
runtime trajectories: 180
total trajectories: 342
turns per trajectory: 4
total turns: 1,368
maximum attempts per turn: 2
maximum request attempts: 2,736
```

The ledger records a unique run ID, comparison-pair ID, workload, episode, replication, condition, condition-order index, cache namespace, turn count, and maximum request-attempt count for every planned trajectory.

Planning is non-executing. The planner has no provider-call command and emits `execution_enabled=false`.

## Freeze procedure

1. Validate every required field.
2. Resolve every explicit unknown or absent field.
3. Verify every referenced artifact exists.
4. Verify every referenced artifact hash.
5. Confirm all required proof gates pass.
6. Confirm no protected or private artifact is referenced.
7. Complete the bounded provider-readiness probe.
8. Declare the approved request and cost budgets.
9. Serialize the manifest canonically.
10. Calculate SHA-256.
11. Record the repository commit containing the frozen manifest.
12. Mark the manifest frozen.
13. Prohibit changes during measured execution.

A changed field creates a new execution-manifest version and requires all affected measured comparisons to be rerun.

## Comparison rule

Runs with different execution-manifest hashes are not comparison-eligible unless a versioned compatibility rule explicitly permits a metric family.

The default is ineligible.

## Current authorization boundary

The current implementation authorizes only:

```text
validate-config
plan
verify
```

It does not authorize:

```text
run
resume
rerun
report measured provider results
```

Measured execution remains blocked until a later change freezes the manifest, resolves all blockers, and adds an explicitly reviewed execution command.
