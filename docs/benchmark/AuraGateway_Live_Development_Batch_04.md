# AuraGateway Live Development Batch 04

## Status

```text
batch_id=auragateway-live-development-batch-04
authorization_id=live-development-batch-04-auth-v1
execution_status=completed_with_accountable_safety_abort
evidence_verification=passed
receipt_acceptance=failed
comparison_eligible=false
```

## Authorized scope

```text
episode=ep-func-001
replication=replication-01
conditions=condition_a,condition_b,condition_c
maximum_runs=3
turns_per_run=4
maximum_attempts=15
maximum_estimated_cost=5000 micro-USD
provider=groq
model_alias=groq-gpt-oss-20b
```

The workload is synthetic Nimbus Relay data. Provider execution, model outputs, failures, telemetry,
latency, pacing, and estimated cost are real runtime observations.

## Observed result

```text
terminal_records=3
attempt_records=9
provider_calls=9
completed_runs=2
provider_error_runs=0
safety_aborts=1
ambiguous_retries_blocked=1
structured_output_failures=0
citation_scope_failures=0
budget_exhaustions=0
estimated_cost_microusd=1438
attempt_budget_respected=true
cost_budget_respected=true
protected_outputs_retained_locally=true
batch_completed=true
receipt_accepted=false
```

Condition A completed all four turns.

Condition B completed all four turns.

Condition C aborted at turn 1, attempt 1 with:

```text
terminal_status=aborted_safety_control
failure_code=AMBIGUOUS_PROVIDER_RESPONSE
provider_error_code=PROVIDER_RESPONSE_AMBIGUOUS
response_certainty=ambiguous
retry_authorized=false
```

## Diagnostic correlation

The public failed-attempt record and protected diagnostic record share the same SHA-256 request
identifier:

```text
1d24e60d5903c5005754d48b4808f7280a40e23b1413c9417171cd86abd70835
```

The protected diagnostic classified the failure as:

```text
family=assistant_content_missing
mapped_provider_error_code=PROVIDER_RESPONSE_AMBIGUOUS
retryable=false
exception_class_allowlisted=null
http_status_code=null
provider_error_type_allowlisted=null
provider_error_code_allowlisted=null
provider_error_param_allowlisted=null
```

This proves deterministic public-to-protected failure correlation without exposing request IDs, prompts,
outputs, provider payloads, or secrets.

## Evidence integrity

Persisted public evidence verification passed. The journal, run records, report, authorization, and
manifest reconcile. All three authorized runs have terminal records. Held-out, full-benchmark, measured
execution, comparison, and benchmark claims remain disabled.

Public evidence hashes:

```text
authorization.json=2c3bdce907b02bd6552f072654981fcb841238ac5a340bfda915bbf96b42e336
journal.jsonl=9988a34831e137e098b377c5a6c424d3b22e8f7340a98023755c9b06c6be98e4
run_records.json=e4a527e092d32cdb4f20498f31c25f5f6fdb2e5b79668663af2db7d2f5c50cf2
report.json=f0b59fd0e1f3e51cd791f7a8a6618efa797b7204524722ac80dab9761600b7a8
manifest.json=74dd2516cf67eda59a7f81019ebee769c7c2e0a5f1d70c373d7ca721fc7a1a06
```

## Workflow decision

Batch 04 must not be rerun or resumed.

The verified failed evidence is preserved. Batch 05 remains blocked until the Groq adapter retains
metadata-safe response-shape diagnostics for assistant-content-missing failures.

Required response-shape fields:

```text
response_id_sha256
response_choice_count
response_finish_reason_allowlisted
assistant_content_state
response_usage_present
response_completion_tokens
reasoning_present
reasoning_byte_count
tool_call_count
refusal_present
refusal_byte_count
```

Prohibited fields remain:

```text
raw reasoning text
raw refusal text
raw tool calls or arguments
raw response ID
raw provider response
raw prompt or retrieved content
credentials or secrets
```

## Claim boundary

Batch 04 establishes real Groq execution over one synthetic development triplet, successful completion of
Conditions A and B, accountable Condition C safety abortion, protected diagnostic correlation, and a
working receipt rejection gate.

It does not establish an accepted A/B/C comparison, cache savings, latency reduction, cost reduction,
quality non-inferiority, held-out performance, deployment safety, or production readiness.
