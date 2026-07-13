# AuraGateway Live Development Batch 06 Authorization

## Purpose

Batch 06 is a fresh development-only live-provider triplet used to exercise the corrected
Groq response boundary and remove the execution-position confound affecting Condition C.

The supplied TLA+ material is conceptual design context only. It is not part of this slice,
is not promoted into the repository, and is not a prerequisite for Batch 06.

## Frozen run selection

Batch 06 selects the already frozen replication-03 order:

```text
condition_c
condition_a
condition_b
```

Exact run IDs:

```text
run-functional-ep-func-001-r03-condition-c
run-functional-ep-func-001-r03-condition-a
run-functional-ep-func-001-r03-condition-b
```

This does not edit the planned-run ledger or invent a new order. It authorizes an existing
counterbalanced replication from the frozen benchmark plan.

## Preserved controls

```text
workload=ep-func-001
provider=groq
model_alias=groq-gpt-oss-20b
turns_per_run=4
maximum_run_count=3
maximum_total_attempt_count=15
maximum_total_cost_microusd=5000
maximum_input_tokens_per_attempt=3000
output_token_budget=256
timeout_seconds=120
minimum_call_interval_seconds=20
rate_limit_cooldown_seconds=65
maximum_cumulative_sleep_seconds=900
```

The corpus, retrieval mode, compiler specification, prompt profile, output contract,
provider adapter identity, quality validation, retry safety, evidence reconciliation, and
receipt gate remain unchanged.

## Acceptance boundary

Batch 06 is accepted only when the receipt gate confirms:

```text
terminal_record_count=3
completed_run_count=3
provider_error_count=0
safety_abort_count=0
budget_exhausted_count=0
structured_output_failure_count=0
citation_scope_failure_count=0
attempt_budget_respected=true
cost_budget_respected=true
protected_outputs_retained_locally=true
verification_passed=true
acceptance_passed=true
```

It remains:

```text
development_only=true
held_out_executed=false
full_benchmark_executed=false
measured_execution_permitted=false
comparison_eligible=false
benchmark_claims_permitted=false
```

## Operational stop rule

Run the authorization exactly once. Clear credentials immediately afterward. Verify public
evidence and request the machine receipt. Do not rerun, resume, stage, commit, or push until
the receipt and evidence have been classified.
