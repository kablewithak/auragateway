# AuraGateway Live Development Batch 03

## Status

```text
batch_id=auragateway-live-development-batch-03
authorization_id=live-development-batch-03-auth-v1
execution_status=completed_with_accountable_failures
evidence_verification=passed
receipt_acceptance=failed
comparison_eligible=false
```

Batch 03 is the first live-development batch governed by a machine-enforced receipt gate.

The receipt gate prevented a complete but unsuccessful provider run from being committed or described as
accepted evidence. The public journal, run records, report, and manifest reconcile, while the stricter
acceptance contract correctly rejects the batch because only one of three authorized runs completed.

## Authorized scope

```text
episode=ep-func-001
replication=replication-01
conditions=condition_a,condition_b,condition_c
runs=3
turns_per_run=4
maximum_attempts=15
maximum_estimated_cost=5000 micro-USD
provider=Groq
model=openai/gpt-oss-20b
```

The workload is synthetic Nimbus Relay data. Provider calls, model outputs, provider failures, token
telemetry, latency, pacing, and estimated cost are real runtime observations.

## Observed result

```text
terminal_records=3
attempt_records=10
provider_calls=10
completed_runs=1
provider_error_runs=2
structured_output_failures=0
citation_scope_failures=0
safety_aborts=0
budget_exhaustions=0
estimated_cost_microusd=1253
attempt_budget_respected=true
cost_budget_respected=true
protected_outputs_retained_locally=true
batch_completed=true
receipt_accepted=false
```

Condition A completed all four turns.

Conditions B and C each completed two turns and then terminated at turn 3 with:

```text
provider_error_code=PROVIDER_RESPONSE_INVALID
terminal_failure_code=NONRETRYABLE_PROVIDER_FAILURE
response_certainty=definite_failure
retry_authorized=false
```

## Receipt gate result

The `run` command returned successfully because the bounded execution completed and every authorized run
received one terminal record.

The separate `receipt` command returned a non-zero exit code because:

```text
completed_run_count != 3
provider_error_count != 0
```

This distinction is intentional:

- `batch_completed=true` means execution accountability is complete;
- it does not mean every run succeeded;
- receipt acceptance requires both accountable evidence and the declared behavioral acceptance conditions.

## Evidence integrity

Persisted public evidence verification passed:

- journal attempt and terminal counts reconcile with run records;
- the report is bound to the Batch 03 authorization;
- all three authorized runs have terminal records;
- the manifest reproduces from the retained files;
- held-out and full benchmark execution remain false;
- measured execution and benchmark claims remain prohibited.

Public evidence hashes:

```text
authorization.json=c1c33cc69cdbfc6cdcb90b5a6e5c44ecb09866fdb5996c952d8990ef6ff1c9ba
journal.jsonl=29cf63ed1d8b576d68c3add3a3a423af7c66708fb694e5f9d98e584a92229d67
run_records.json=8a04e6dd6bdccc5b68f1517883b5355a5caf49f96120f8ade7c1a17448bef446
report.json=83b1fc27596ac15bdb291e63fc05e5eb5a2ccf5a75a8ce426bd5fbcb3dce84d4
manifest.json=524926a3977339d3a3e45a2bd86188b99c2b99e282b6d8a4c15c32d4bbe97580
```

Protected evidence remains ignored under `.local/benchmark/live-development-v3/`.

## Workflow decision

Batch 03 must not be rerun or resumed.

The failed evidence is preserved as an immutable, verified development-run bundle. The next live
authorization is blocked until the provider adapter retains enough metadata-safe diagnostic evidence to
distinguish provider request rejection, SDK validation failure, empty assistant output, and other
unsupported exceptions without storing raw provider error bodies or generated content.

## Claim boundary

Batch 03 establishes:

- real Groq invocation on one synthetic development A/B/C triplet;
- successful completion of Condition A;
- accountable failure retention for Conditions B and C;
- functioning pacing, budget, protected-output, verification, and receipt controls;
- successful prevention of a false acceptance claim.

It does not establish:

- an accepted A/B/C comparison;
- cache-reuse improvement;
- latency or cost reduction;
- quality non-inferiority;
- held-out or full benchmark performance;
- customer-data readiness;
- deployment safety;
- production readiness.
