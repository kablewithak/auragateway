# AuraGateway Evidence Bundle Specification

## Document control

```text
Specification version: 0.1.0
Status: Phase 0 design control
Applies to: dry runs, functional benchmarks, runtime microbenchmarks, paired A/B/C reports
Storage posture: local-first
```

## Purpose

The evidence bundle is the inspectable unit behind an AuraGateway result.

A report without a complete bundle is not benchmark evidence.

## Bundle states

```text
building
validation_failed
finalized
superseded
```

Only a `finalized` bundle may support a benchmark claim.

A finalized bundle is immutable.

## Bundle types

### Validation bundle

Used for configuration checks and deterministic fixture execution.

May omit comparative result files when no comparison was scheduled.

### Functional benchmark bundle

Contains task-quality, routing, validation, citation, and feedback evidence.

### Runtime microbenchmark bundle

Contains cache, token, timing, route, cost, and failure-accounting evidence.

### Complete comparison bundle

References or contains the functional and runtime result sets required for the final A/B/C report.

## Required directory shape

```text
<evidence_bundle_id>/
  bundle_manifest.json
  benchmark_manifest.json
  configuration_fingerprint.json
  environment_manifest.json
  run_results.jsonl
  failures.jsonl
  exclusions.jsonl
  reruns.jsonl
  comparison_eligibility.json
  comparison.csv
  benchmark_report.md
  sanitized_trace_samples.jsonl
  artifact_hashes.json
```

Protected review exports and raw provider payloads are forbidden in this directory.

## Bundle manifest fields

```text
schema_version
evidence_bundle_id
bundle_type
bundle_status
created_at
finalized_at
run_group_id
benchmark_constitution_version
benchmark_constitution_hash
benchmark_manifest_hash
configuration_fingerprint
git_commit_hash
artifact_hash_manifest_hash
supersedes_bundle_id
supersession_reason
permitted_claim_families
blocked_claim_families
```

## Environment manifest fields

```text
python_version
dependency_lock_hash
operating_system_family
provider_model_alias
provider_adapter_version
benchmark_runner_version
route_policy_version
telemetry_rules_version
pricing_schedule_version
documentation_dates_checked
```

Do not include usernames, machine names, home-directory paths, tokens, or secrets.

## Run result fields

Every scheduled run includes:

```text
run_id
trace_id
comparison_pair_id
episode_id
replication_id
condition_id
turn_count
terminal_status
provider_model_alias
configuration_fingerprint
started_at
completed_at
quality_summary
runtime_summary
failure_labels
artifact_references
```

Raw prompts, retrieved text, model outputs, and provider payloads are forbidden.

## Failure record fields

```text
run_id
trace_id
failure_code
failure_stage
retryable
response_state
safe_message
affected_metrics
affected_claims
occurred_at
```

## Exclusion record fields

```text
run_id
exclusion_reason_code
predeclared_rule_id
excluded_metric_families
remains_in_failure_accounted_view
decision_timestamp
```

## Rerun record fields

```text
original_run_id
replacement_run_id
rerun_reason_code
trigger_type
original_remains_in_denominator
decision_timestamp
```

## Comparison eligibility fields

```text
schema_version
comparison_contract_version
eligible
partially_eligible
compared_run_ids
eligible_metric_families
ineligible_metric_families
mismatched_fields
invalidated_claims
required_reruns
reason_codes
```

## Artifact hash manifest

Every retained file is listed with:

```text
relative_path
artifact_type
schema_version
byte_count
sha256
```

The hash manifest does not include itself.

`bundle_manifest.json` records the SHA-256 of `artifact_hashes.json`.

## Finalization algorithm

1. Validate all required files and schemas.
2. Confirm every scheduled run has one terminal state.
3. Confirm comparison eligibility was evaluated.
4. Confirm telemetry sufficiency was evaluated for requested claim families.
5. Confirm forbidden private files are absent.
6. Generate reports only from machine-readable artifacts.
7. Generate `artifact_hashes.json`.
8. Record the hash-manifest hash in `bundle_manifest.json`.
9. Set the bundle status to `finalized`.
10. Reject further writes to the bundle.

## Supersession

A correction never mutates the finalized bundle.

The replacement bundle must declare:

```text
supersedes_bundle_id
supersession_reason
affected_artifacts
affected_claims
rerun_scope
```

The prior bundle remains inspectable.

## Verification

A bundle verifier must check:

- required paths;
- JSON/JSONL schema validity;
- terminal run accounting;
- artifact byte counts;
- artifact hashes;
- manifest references;
- comparison-eligibility consistency;
- report-to-result consistency;
- absence of forbidden private artifacts.

Verification output must be machine-readable and return a non-zero process exit on failure.

## Claims boundary

A bundle may support only claim families listed as permitted in its manifest.

Examples:

```text
task_quality
structured_output
citation_support
route_policy
cache_evidence
latency
estimated_cost
feedback_evidence
```

A claim family remains blocked when:

- telemetry is insufficient;
- quality non-inferiority fails;
- comparison is ineligible;
- required run counts are incomplete;
- provider semantics are unresolved;
- bundle verification fails.

## Local-first storage

Initial paths:

```text
evidence_vault/     finalized sanitized project evidence
.local/runs/        in-progress execution artifacts
.local/review/      protected blinded-review exports
.local/provider/    ephemeral adapter debugging only
```

Only explicitly approved sanitized evidence belongs in `evidence_vault/`.

No cloud storage is required for the current project.
