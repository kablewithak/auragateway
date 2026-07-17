# Semi-Formal Reasoning Certificate

## AuraGateway Reconcile-Balance Action-Extraction Requalification v2

```text
certificate_id=AURAGATEWAY-LOCAL-ABC-SFRC-0004
schema_version=2.0.0
status=CERTIFIED_PASSED_WITH_TRACEABILITY_AND_RUNTIME_WARNINGS
quality_result=16_OF_16_EXACT_OPERANDS_AND_FINAL_ANSWERS
authorization_consumed=true
rerun_permitted=false
next_gate=action_extraction_v2_traceability_cleanup_hardening
```

## 1. Certificate Scope

This certificate determines whether the completed AuraGateway reconcile-balance
requalification v2:

1. executed the complete authorized 16-case suite;
2. satisfied the exact action-extraction quality gate;
3. preserved the fixed one-attempt execution constitution;
4. produced evidence sufficient to exclude silent request failures;
5. maintained complete traceability between executed prompts and retained scores;
6. completed with a perfectly clean runtime shutdown; and
7. may be executed again under the same authorization.

This certificate does not authorize another execution.

## 2. Method

This certificate uses a semi-formal structure:

```text
definitions
    -> premises
    -> evidence trace
    -> alternative-hypothesis checks
    -> formal derivation
    -> bounded conclusion
```

The structure forces each conclusion to bind to retained evidence and prevents the
quality result, traceability result, cleanup result, and authorization disposition
from being collapsed into one unsupported narrative judgment.

The executed evidence remains the source of truth. Semi-formal reasoning organizes
and checks that evidence; it does not replace execution.

## 3. Immutable Evidence Bindings

```text
evidence_archive_filename=
auragateway-reconcile-balance-action-extraction-requalification-evidence-v2.zip

evidence_archive_sha256=
b7da2b703232154742665b47254e662a2e6ff4b6e198827e7d29f67dc9c16c93

evidence_archive_size_bytes=22767
evidence_member_count=8

notebook_sha256=
e1e38afa6f269c9aa529bdafa1ce4ca8c4bba4a53d7b69e93bfaf0e3549a97e9

authorization_sha256=
a2a35e3fb566ed697089dd41c962c7d932490eaeda3ab12f1f3955c285225899

execution_package_sha256=
deb7d803819ec489218f78ecc4466ae1402eef30a63ba7b93d293ea872677451

package_merge_commit=
52dcd0564b26b917684faedaa46d2d038a9e0be7

execution_repository_commit=
639e21a63eb8a37d0221c2630b756203d1270f62
```

The protected evidence archive remains outside Git.

## 4. Definitions

### D1 — Complete Governed Execution

A run is a complete governed execution if and only if:

- all 16 authorized cases appear exactly once;
- ledger sequence numbers are exactly 1 through 16;
- every case uses `attempt_index=1`;
- no hidden retry, repair, replacement request, or failed-case-only execution
  occurs; and
- the complete ledger and evaluation artifacts are retained.

### D2 — Exact Action-Extraction Success

A case succeeds exactly if:

- the response is HTTP 200;
- the response body is valid JSON;
- the extracted action satisfies the frozen action schema;
- case identity and turn identity are exact;
- opening balance, credits, and debits match the expected operands;
- deterministic execution of the action succeeds; and
- the resulting final answer matches the expected answer.

### D3 — Quality-Gate Pass

The requalification quality gate passes if and only if:

```text
completed_requests=16
exact_operand_matches=16
exact_final_answer_matches=16
semantic_failures=0
infrastructure_failures=0
```

### D4 — Traceability-Clean Evidence

Evidence is traceability-clean only if every retained scoring object identifies
the same prompt policy and rendered prompt that produced the corresponding model
request.

### D5 — Perfectly Clean Shutdown

Shutdown is perfectly clean only if:

- the worker exits with return code zero;
- the worker port closes;
- application shutdown completes;
- no forced child-process termination is required; and
- no leaked process, shared-memory, semaphore, or resource warning remains.

### D6 — Warning-Qualified Pass

A run is a warning-qualified pass when:

- the execution and quality gates pass;
- retained evidence remains sufficient to establish what was executed;
- non-invalidating traceability or runtime defects are present; and
- those defects are explicitly preserved rather than hidden.

## 5. Premises

### P1 — Archive Integrity

The evidence ZIP:

- matches the frozen SHA-256;
- contains exactly eight expected members;
- passes ZIP integrity validation;
- preserves the expected member order; and
- preserves every expected member digest.

### P2 — Complete Case Constitution

The schedule and ledger contain exactly the 16 authorized case IDs in the frozen
order. No case is missing, duplicated, replaced, or executed outside the
authorized schedule.

### P3 — One-Attempt Constitution

Every ledger record reports:

```text
attempt_index=1
```

The aggregate evidence reports:

```text
hidden_retries=0
repair_attempts=0
replacement_requests=0
failed_case_only_execution=false
```

### P4 — Transport and Schema Results

All 16 requests produced:

```text
HTTP_200=16/16
valid_JSON=16/16
valid_action_schema=16/16
exact_case_identity=16/16
exact_turn_identity=16/16
finish_reason=stop
```

### P5 — Quality Results

The retained evaluation and report record:

```text
exact_operand_matches=16/16
deterministic_execution_successes=16/16
exact_final_answer_matches=16/16
semantic_failures=0
infrastructure_failures=0
```

### P6 — Actual v2 Prompt Identity

The frozen schedule and outer ledger bind the executed v2 prompt policy:

```text
750a6f89c7ada7b9d508eaf143214e3d93e6456bb4b3586afa7dc089f8dcfc4c
```

The retained normalized-prompt, rendered-prompt, and request-body hashes match the
frozen 16-case schedule.

### P7 — Nested Score Metadata Divergence

All 16 nested score objects retain the legacy prompt-policy identity:

```text
5f5415b907552bad09dfe16f0537dac0834fd42493579d91090d1b416daa2ec9
```

This differs from the v2 prompt-policy identity bound by the schedule and outer
ledger.

### P8 — Declared Cleanup State

The report declares:

```text
cleanup_status=CLEAN
worker_return_code=0
worker_port_closed=true
```

### P9 — Observed Cleanup Warnings

The worker log records:

```text
force killing remaining processes count=1
1 leaked semaphore object
```

The archive contains seven classified non-fatal runtime warning families.

### P10 — Privacy Boundary

The retained evidence confirms:

```text
raw_prompt_retained=false
raw_output_retained=false
raw_action_retained=false
token_ids_retained=false
credentials_retained=false
customer_data_used=false
external_spend=0
```

### P11 — Authorization Lifecycle

The one-shot v2 authorization was used for the completed 16-request execution.
Its lifecycle state is therefore:

```text
authorization_consumed=true
authorization_reusable=false
```

## 6. Evidence Trace

| Claim | Evidence | Result |
|---|---|---|
| C1: The complete authorized suite executed | Sixteen unique case IDs, sequence 1–16, complete ledger | Proven |
| C2: No request silently disappeared | Sixteen scheduled requests and sixteen terminal ledger records | Proven |
| C3: No hidden retry occurred | Every record has attempt index 1; aggregate retry count is zero | Proven |
| C4: Every response crossed the model boundary successfully | 16/16 HTTP 200, valid JSON, and valid schema | Proven |
| C5: Both historical semantic failures passed in the fixed suite | 16/16 exact operands and answers, including formatted-currency and key-value cases | Proven for the fixed suite |
| C6: The actual requests used the v2 prompt | Schedule and outer-ledger prompt and request hashes match frozen v2 identities | Proven |
| C7: Nested score metadata is fully trustworthy | Nested score prompt-policy identities retain a legacy hash | Refuted |
| C8: Shutdown was perfectly graceful | Forced process termination and leaked semaphore warning occurred | Refuted |
| C9: Shutdown reached a safe terminal state | Worker return code zero, port closed, application shutdown complete | Proven |
| C10: The authorization remains unused | Completed execution consumed the one-shot authorization | Refuted |

## 7. Alternative-Hypothesis Checks

### H1 — The 16/16 result is invalid because the wrong prompt was executed

**Expected evidence if H1 were true:**

- schedule prompt hashes would differ from the frozen v2 dry run;
- outer-ledger rendered-prompt hashes would differ from scheduled hashes;
- request-body hashes would not match the frozen schedule; and
- only the legacy prompt identity would appear in request-level evidence.

**Observed evidence:**

- the schedule binds the v2 prompt policy;
- normalized and rendered prompt hashes match the frozen v2 schedule;
- request-body hashes match; and
- the divergence is confined to nested score metadata.

**Conclusion:**

```text
H1=REFUTED
```

The stale nested metadata is a traceability defect, not proof that the wrong prompt
was executed.

### H2 — The run suffered an unreported model or transport failure

**Expected evidence if H2 were true:**

- fewer than 16 terminal ledger records;
- non-200 responses;
- invalid JSON;
- transport failure codes;
- missing cases; or
- infrastructure-failure count greater than zero.

**Observed evidence:**

```text
terminal_records=16
HTTP_200=16
valid_JSON=16
infrastructure_failures=0
```

**Conclusion:**

```text
H2=REFUTED
```

No silent request or transport failure is supported by the evidence.

### H3 — Cleanup was perfectly clean

**Expected evidence if H3 were true:**

- no forced process termination;
- no leaked semaphore or resource warning; and
- no cleanup-related warning classification.

**Observed evidence:**

```text
forced_process_termination_count=1
leaked_semaphore_warning=true
```

**Conclusion:**

```text
H3=REFUTED
```

The declared `CLEAN` label overstates the observed shutdown quality.

### H4 — Cleanup warnings invalidate the completed quality result

**Expected evidence if H4 were true:**

- worker termination before all 16 responses were recorded;
- missing or corrupt ledger records;
- an open worker port;
- a non-zero worker return code; or
- incomplete evaluation artifacts.

**Observed evidence:**

- all 16 responses and evaluations were retained;
- the worker returned zero;
- the port closed; and
- the evidence archive completed successfully.

**Conclusion:**

```text
H4=REFUTED
```

The cleanup warnings require hardening but do not invalidate the completed request
and quality evidence.

### H5 — A rerun is required to establish confidence

**Expected justification if H5 were true:**

- incomplete evidence;
- missing cases;
- ambiguous quality outcome; or
- an unused authorization.

**Observed evidence:**

- complete 16-case evidence;
- an unambiguous 16/16 outcome; and
- a consumed one-shot authorization.

**Conclusion:**

```text
H5=REFUTED_AND_PROHIBITED
```

A rerun is neither necessary nor authorized.

## 8. Formal Derivation

### F1 — Execution Completeness

From P2, P3, and P4:

- all authorized cases executed;
- each case executed exactly once; and
- every case reached a valid terminal response.

Therefore, by D1:

```text
complete_governed_execution=true
```

### F2 — Quality Result

From P4 and P5:

```text
completed_requests=16
exact_operand_matches=16
exact_final_answer_matches=16
semantic_failures=0
infrastructure_failures=0
```

Therefore, by D2 and D3:

```text
quality_gate_passed=true
```

### F3 — Traceability Result

From P6, request-level evidence proves use of the v2 prompt construction.

From P7, nested score objects retain an incorrect legacy prompt-policy identity.

Therefore, by D4:

```text
traceability_clean=false
quality_result_invalidated=false
```

The correct classification is a non-invalidating traceability warning.

### F4 — Cleanup Result

From P8, the worker returned zero and the port closed.

From P9, forced process termination and a leaked semaphore warning occurred.

Therefore, by D5:

```text
perfectly_clean_shutdown=false
audited_cleanup_status=CLEAN_WITH_RUNTIME_WARNINGS
```

### F5 — Authorization Disposition

From P11, the authorized 16-request execution completed.

Therefore:

```text
authorization_consumed=true
authorization_reuse_permitted=false
notebook_rerun_permitted=false
failed_case_only_rerun_permitted=false
```

## 9. Formal Conclusion

The execution satisfies the complete 16-case governed execution boundary.

The action-extraction quality gate passed with:

```text
16/16 exact operand matches
16/16 exact final-answer matches
0 semantic failures
0 infrastructure failures
0 retries
0 repairs
0 replacement requests
```

The request-level schedule and ledger prove that the v2 remediation prompt and
schema were used.

However:

1. all 16 nested score objects retain stale legacy prompt-policy metadata; and
2. the worker required forced remaining-process termination and emitted a leaked
   semaphore warning.

These findings do not invalidate the completed quality result, but they prevent
classification as a perfectly clean run.

Therefore:

```text
CERTIFICATE_STATUS=
CERTIFIED_PASSED_WITH_TRACEABILITY_AND_RUNTIME_WARNINGS

QUALITY_RESULT=
16_OF_16_EXACT_OPERANDS_AND_FINAL_ANSWERS

AUDITED_CLEANUP_STATUS=
CLEAN_WITH_RUNTIME_WARNINGS

AUTHORIZATION_STATUS=CONSUMED
RERUN_STATUS=PROHIBITED
```

## 10. Required Next Gate

```text
action_extraction_v2_traceability_cleanup_hardening
```

The next slice must:

- propagate the active prompt-policy and rendered-prompt identities into scoring
  objects;
- prevent legacy score metadata from surviving a versioned intervention;
- classify forced cleanup and resource leaks accurately;
- distinguish graceful shutdown from safe-but-warning-qualified shutdown;
- add fixed local regression tests for both findings;
- perform no model request;
- perform no GPU execution; and
- reuse no consumed authorization.

## 11. Non-Claims

This certificate does not claim:

- that nested score metadata was fully correct;
- that vLLM shutdown was perfectly graceful;
- that remediation generalizes beyond the fixed 16-case suite;
- that formatted-number normalization is a general financial parser;
- that cache reuse, latency, or cost savings were measured;
- that the full A/B/C benchmark is authorized;
- that another execution is permitted; or
- that AuraGateway is production-ready.

## 12. Final Certificate Record

```text
certificate_id=AURAGATEWAY-LOCAL-ABC-SFRC-0004
status=CERTIFIED_PASSED_WITH_TRACEABILITY_AND_RUNTIME_WARNINGS
quality_result=16_OF_16_EXACT_OPERANDS_AND_FINAL_ANSWERS
traceability_finding_count=1
cleanup_finding_count=1
runtime_warning_count=7
authorization_consumed=true
rerun_permitted=false
full_abc_authorized=false
next_gate=action_extraction_v2_traceability_cleanup_hardening
```
