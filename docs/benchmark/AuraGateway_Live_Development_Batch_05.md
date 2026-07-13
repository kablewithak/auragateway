# AuraGateway Live Development Batch 05

## Final status

```text
authorization_id=live-development-batch-05-auth-v1
batch_id=auragateway-live-development-batch-05
classification=FAILED_VERIFIED
terminal_record_count=3
attempt_record_count=3
completed_run_count=0
provider_error_count=3
safety_abort_count=0
batch_completed=true
evidence_verification=passed
receipt_acceptance=failed
rerun_permitted=false
resume_permitted=false
```

## Scope

Batch 05 was a development-only A/B/C replication against Groq
`openai/gpt-oss-20b`.

It did not execute held-out or full-benchmark workloads. It did not permit benchmark,
measured, or comparison claims.

## Observed result

All three conditions terminated on turn 1:

```text
condition_a=provider_error
condition_b=provider_error
condition_c=provider_error
failure_code=NONRETRYABLE_PROVIDER_FAILURE
provider_error_code=PROVIDER_RESPONSE_INVALID
response_certainty=definite_failure
```

The report retained:

```text
terminal_record_count=3
attempt_record_count=3
provider_call_count=3
completed_run_count=0
provider_error_count=3
protected_outputs_retained_locally=false
total_estimated_cost_microusd=0
```

The zero estimated cost means usage telemetry was unavailable after typed response
validation failed. It does not establish that provider execution was free.

## Failure diagnosis

Each protected diagnostic recorded:

```text
schema_version=1.1.0
family=response_schema_invalid
exception_class_allowlisted=ValidationError
mapped_provider_error_code=PROVIDER_RESPONSE_INVALID
retryable=false
```

The adapter rejected the SDK response before assistant-content inspection, output
normalization, telemetry extraction, or protected-output retention.

The compatibility divergence was a nullable optional SDK field:

```text
message.tool_calls=null
```

The adapter contract expected a non-null tuple. The local synthetic response fixtures had
normalized absent tool calls to an empty list, so the explicit-null SDK shape was not covered.

## Resolution

The adapter now accepts:

```python
tool_calls: tuple[object, ...] | None = None
```

Tool-call count is computed with:

```python
len(choice.message.tool_calls or ())
```

The diagnostic schema is upgraded to `1.2.0` for future failures. A typed validation failure
may retain only:

- bounded error count;
- allowlisted model-field locations;
- allowlisted Pydantic error types.

It does not retain failed values, raw response payloads, exception messages, prompts,
documents, provider output, tool arguments, credentials, or secrets.

## Evidence boundary

Batch 05 remains immutable failed evidence.

Do not rerun or resume it. The compatibility correction must be exercised only through a new
Batch 06 authorization after this closeout is merged.

This batch establishes harness failure detection and preserved execution accountability. It
does not establish provider reliability, output quality, cache performance, latency
improvement, cost improvement, deployment safety, or production readiness.
