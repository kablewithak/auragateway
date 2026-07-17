# AuraGateway Semi-Formal Reasoning Certificate

## Certificate Identity

**Certificate ID:** `AURAGATEWAY-LOCAL-ABC-SFRC-0003`
**Issued:** 2026-07-17
**Project:** AuraGateway v2 — Cache-Aware Agent Runtime and Evaluation Harness
**Subject:** Reconcile-Balance Action-Extraction Canary v1
**Certificate type:** Engineering evidence and reasoning certificate
**Formal mathematical proof:** No
**Reasoning standard:** Semi-formal, evidence-bound, reproducible hash verification
**Confidence:** High
**Terminal classification:** `CERTIFIED_FAILED_DIAGNOSTIC_WITH_CLEAN_HARNESS`
**Authorization state:** Consumed
**Further execution under the same authorization:** Prohibited
**Customer data used:** False
**External spend:** R0 / $0

> This certificate records an engineering conclusion from frozen synthetic evidence. It is not a legal, regulatory, financial, or production-readiness certification.

---

# 1. Certified Conclusion

The governed 12-request reconcile-balance action-extraction canary completed without infrastructure failure and produced a valid failed diagnostic.

The model returned structurally valid actions for all 12 fixed cases, but two actions contained incorrect business operands. Deterministic execution faithfully executed those incorrect actions, producing two wrong final answers.

The certified result is:

```text
status=ACTION_EXTRACTION_CANARY_FAILED_DIAGNOSTIC
authorized_requests=12
completed_requests=12
http_200_responses=12
valid_action_json=12
valid_action_schema=12
exact_identity_matches=12
deterministic_execution_successes=12
exact_operand_matches=10
exact_final_answer_matches=10
semantic_failures=2
infrastructure_failures=0
cleanup_status=CLEAN
authorization_consumed=true
same_authorization_rerun_permitted=false
```

The two certified failure modes are:

```text
FORMATTED_INTEGER_LEADING_COMPONENT_DROPPED
KEY_VALUE_CREDIT_DEBIT_ROLE_REVERSAL
```

The next permitted engineering gate is:

```text
IMMUTABLE_EVIDENCE_AUDIT_AND_FAILURE_DISPOSITION
```

No new GPU execution should occur until the evidence audit is landed and a separately versioned remediation receives a new bounded authorization.

---

# 2. Evidence Identity

## 2.1 Evidence archive

```text
filename=auragateway-reconcile-balance-action-extraction-canary-evidence-v1.zip
sha256=412db1700b6505502ca9afc83981738c9f50f043bad6de37e015ab7f3a9944c8
size_bytes=18837
zip_integrity=passed
member_count=8
```

## 2.2 Governing execution identity

```text
authorization_fingerprint=9efe45c37b3223b6f01bd55e6471a1c487b5115ba6260b77bd3a6ff2219933a9
authorization_merge_commit=0619867a7acbee5e4c5b639963cf1046cbf36809
repository_commit=0619867a7acbee5e4c5b639963cf1046cbf36809
notebook_sha256=b0d3f840e6d334c6b7631431228ef9ff50a7ea55f8eabceb65fcf4685a1ad5ab
worker_id=worker_1
required_request_count=12
```

## 2.3 Runtime identity

```text
runtime_policy=isolated_venv_exact_torch_cu129_v2
venv_bootstrap_policy=without_pip_host_pip_python_v1
system_site_packages_inherited=false
torch=2.11.0+cu129
torch_cuda=12.9
vllm_module=0.25.1
vllm_distribution=0.25.1+cu129
gpu_count=2
gpu_model=Tesla T4
compute_capability=7.5
binary_import_probe=passed
```

## 2.4 Model identity

```text
model_repository=Qwen/Qwen2.5-0.5B-Instruct
model_revision=7ae557604adf67be50417f59c2c2f167def9a775
model_weights_sha256=fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe
```

---

# 3. Premises

The certificate relies on the following premises.

## P1 — Frozen authorization

The execution was bound to one authorization fingerprint, one notebook hash, one model revision, one runtime identity, one worker, and exactly 12 fixed requests.

## P2 — One-attempt policy

Each fixed case permitted exactly one request attempt.

```text
hidden_retry_count=0
repair_attempt_count=0
replacement_request_count=0
direct_model_arithmetic_fallback_used=false
```

## P3 — Complete request execution

The checkpoint and final report agree that all 12 required requests completed.

```text
completed_request_count=12
required_request_count=12
```

## P4 — No infrastructure failure

The checkpoint reports:

```text
infrastructure_failure_count=0
infrastructure_failure=null
```

All ledger entries returned HTTP 200.

## P5 — Clean worker lifecycle

The final report records:

```text
cleanup_status=CLEAN
signal_path=SIGINT
return_code=0
port=8001
port_closed=true
```

## P6 — Structural validity

The evaluation report records:

```text
action_json_valid=12/12
action_schema_valid=12/12
identity_accuracy=12/12
execution_success=12/12
```

## P7 — Semantic gate failure

The evaluation report records:

```text
operand_accuracy=10/12
final_answer_accuracy=10/12
first_attempt_task_success=10/12
gate_decision=failed
```

## P8 — Exact failed case set

The final report and evaluation report agree that the failed case IDs are exactly:

```text
formatted-currency-values
key-value-layout
```

## P9 — Privacy boundary

The final report records:

```text
raw_prompt_retained=false
raw_output_retained=false
raw_action_retained=false
customer_data_used=false
```

## P10 — Deterministic execution contract

The trusted executor computes:

```text
answer = opening_balance + credits - debits
```

The model supplies the typed operands. Deterministic code supplies the arithmetic result.

## P11 — Canonical action fingerprinting

A typed action is serialized as canonical sorted JSON and hashed with SHA-256.

## P12 — Canonical result fingerprinting

A deterministic result includes the answer and the action SHA-256, is canonically serialized, and is hashed with SHA-256.

## P13 — Fixed case ground truth

The frozen manifest supplies unambiguous expected operands for both failed cases.

## P14 — Cache evidence exclusion

The authorization explicitly records:

```text
cache_measurement_in_scope=false
cache_claims_permitted=false
```

## P15 — Full benchmark exclusion

The authorization and final report record:

```text
full_measured_rerun_authorized=false
```

---

# 4. Reasoning Trace

## R1 — Infrastructure classification

From P3, P4, and P5:

- every authorized request completed;
- no infrastructure failure was recorded;
- the worker exited cleanly;
- the serving port closed.

Therefore:

```text
the terminal failure is not an infrastructure abort
```

## R2 — Parsing and schema classification

From P6:

- all outputs were valid JSON;
- all outputs passed the action schema;
- every action matched the fixed case identity and turn identity.

Therefore:

```text
the terminal failure is not a JSON, schema, case-ID, or turn-ID failure
```

## R3 — Deterministic executor classification

From P6 and P10:

- all 12 typed actions reached deterministic execution;
- deterministic execution completed successfully for all 12.

Therefore:

```text
the terminal failure is not a deterministic arithmetic executor failure
```

## R4 — Semantic extraction classification

From P7 and P8:

- only 10 of 12 actions matched the exact operands;
- the same 10 of 12 produced the correct final answer;
- the two operand failures are the same two final-answer failures.

Therefore:

```text
the terminal failure is a semantic operand-extraction failure
```

## R5 — Failed diagnostic classification

From R1 through R4:

- the harness, transport, schema, identity, and executor boundaries operated;
- the model supplied two schema-valid but semantically incorrect actions;
- the gate correctly rejected the run.

Therefore:

```text
ACTION_EXTRACTION_CANARY_FAILED_DIAGNOSTIC
```

is the correct terminal classification.

---

# 5. Hash-Resolved Failure Proofs

Raw model outputs and raw actions were intentionally not retained. The exact observed actions were recovered by testing prompt-grounded candidate operands against both the retained action hash and retained deterministic-result hash.

A candidate is accepted only when:

```text
candidate_action_sha256 == retained_action_sha256
and
candidate_result_sha256 == retained_result_sha256
and
candidate_answer == opening_balance + credits - debits
```

This is a dual-hash resolution, not an inference from final answer alone.

## 5.1 Failure A — Formatted currency value

### Frozen prompt ground truth

```json
{
  "opening_balance": 1200,
  "credits": 300,
  "debits": 50,
  "expected_answer": 1450
}
```

### Retained evidence

```text
eval_case_id=formatted-currency-values
action_sha256=6b74eea6c5d3430390068dad20e9932b82e84b821252c7a2103cb93924dc304b
result_sha256=4d255be4764ee2679eebc6be05249ff0bf87700d65be21e51da79bdf9f5b9a5e
evaluation_failure_codes=FINAL_ANSWER_MISMATCH,OPERAND_MISMATCH
```

### Exact hash-resolved action

```json
{
  "schema_version": "1.0.0",
  "capability": "arithmetic.reconcile_balance.v1",
  "case_id": "payment-reconciliation",
  "turn_index": 1,
  "opening_balance": 200,
  "credits": 300,
  "debits": 50
}
```

### Deterministic result

```text
200 + 300 - 50 = 450
```

### Reproduction

```text
reconstructed_action_sha256=6b74eea6c5d3430390068dad20e9932b82e84b821252c7a2103cb93924dc304b
reconstructed_result_sha256=4d255be4764ee2679eebc6be05249ff0bf87700d65be21e51da79bdf9f5b9a5e
```

Both hashes exactly match the retained evidence.

### Certified failure label

```text
FORMATTED_INTEGER_LEADING_COMPONENT_DROPPED
```

### Certified interpretation

The model treated `R1,200` as `200`, while correctly extracting `R300` and `R50`.

This is a semantic number-normalization error. It is not a JSON, schema, identity, or deterministic-execution error.

---

## 5.2 Failure B — Key-value field reversal

### Frozen prompt ground truth

```json
{
  "opening_balance": 5000,
  "credits": 250,
  "debits": 1250,
  "expected_answer": 4000
}
```

### Retained evidence

```text
eval_case_id=key-value-layout
action_sha256=bd5c297bb523706089530596576da835e8d7c7895842622328d381258db2d139
result_sha256=5b66dcbc8a06a470a6257f35bb109136eef13bdcd6799e5fa25362f9dae96d88
evaluation_failure_codes=FINAL_ANSWER_MISMATCH,OPERAND_MISMATCH
```

### Exact hash-resolved action

```json
{
  "schema_version": "1.0.0",
  "capability": "arithmetic.reconcile_balance.v1",
  "case_id": "payment-reconciliation",
  "turn_index": 1,
  "opening_balance": 5000,
  "credits": 1250,
  "debits": 250
}
```

### Deterministic result

```text
5000 + 1250 - 250 = 6000
```

### Reproduction

```text
reconstructed_action_sha256=bd5c297bb523706089530596576da835e8d7c7895842622328d381258db2d139
reconstructed_result_sha256=5b66dcbc8a06a470a6257f35bb109136eef13bdcd6799e5fa25362f9dae96d88
```

Both hashes exactly match the retained evidence.

### Certified failure label

```text
KEY_VALUE_CREDIT_DEBIT_ROLE_REVERSAL
```

### Certified interpretation

The model retained all three numeric values but reversed the semantic roles of credits and debits.

This is a named-field binding error. It is not a numeric parsing, JSON, schema, identity, or deterministic-execution error.

---

# 6. Alternative Explanations Considered

## A1 — HTTP or transport failure

Rejected because all 12 ledger entries returned HTTP 200 and the infrastructure failure count is zero.

## A2 — Invalid JSON

Rejected because action JSON validity is 12/12.

## A3 — Invalid action schema

Rejected because action schema validity is 12/12.

## A4 — Wrong case or turn identity

Rejected because identity accuracy is 12/12.

## A5 — Arithmetic executor defect

Rejected because deterministic execution success is 12/12 and the retained result hashes reproduce exactly from the hash-resolved actions.

## A6 — Hidden retry or repair contamination

Rejected because hidden retries, repairs, and replacements are all zero.

## A7 — Direct model arithmetic fallback

Rejected because direct model arithmetic fallback was false for every case.

## A8 — Customer-data ambiguity

Rejected because every case is synthetic and customer data was not used.

## A9 — Cache behaviour caused the quality result

Not established. Cache measurement and cache claims were outside the authorized scope.

## A10 — One generic failure mechanism explains both cases

Rejected. The first failure changes one formatted integer while preserving field roles. The second preserves all values but reverses two field roles. They are distinct failure families.

---

# 7. Authorization Decision

The one-shot authorization is consumed because all 12 authorized requests were executed.

```text
authorization_consumed=true
same_authorization_rerun_permitted=false
retry_only_failed_cases_permitted=false
full_measured_rerun_authorized=false
```

A rerun under the same notebook and authorization would violate the fixed one-attempt execution contract and contaminate the evidence lineage.

Any future execution requires:

1. immutable audit of this evidence;
2. a versioned remediation;
3. fixed regression cases;
4. new notebook and artifact hashes;
5. a new bounded authorization;
6. no hidden retry, repair, or replacement path.

---

# 8. Permitted Claims

The following claims are certified:

- The isolated Torch/vLLM runtime passed its binary import probe.
- The worker started, served all 12 requests, and shut down cleanly.
- All 12 model responses were HTTP 200.
- All 12 responses were valid JSON.
- All 12 responses passed the strict action schema.
- All 12 matched the required case and turn identities.
- All 12 actions executed deterministically.
- Ten actions contained the exact operands.
- Ten actions produced the exact expected answer.
- Two schema-valid actions contained incorrect operands.
- The two exact semantic failures are hash-resolved and reproducible.
- No raw prompts, raw outputs, or raw actions were retained.
- No customer data was used.
- No retries, repairs, or replacement requests occurred.
- The gate correctly failed.
- The authorization is consumed.

---

# 9. Non-Claims

This certificate does not establish:

- that the action-extraction canary passed;
- that structured output guarantees semantic correctness;
- that action extraction is production-safe;
- that the model is generally 83.33% accurate;
- that the intervention improved all cases over a matched baseline;
- that cache savings were measured;
- that cache behaviour preserved quality;
- that the full A/B/C benchmark is authorized;
- that the full A/B/C benchmark would pass;
- that the model is unsuitable for all extraction tasks;
- that either failure can be fixed by prompting alone;
- that the run used production or customer data;
- that AuraGateway is deployed;
- that AuraGateway is production-ready;
- that this is a legal or regulatory certification.

---

# 10. Required Next Gate

```text
gate=IMMUTABLE_EVIDENCE_AUDIT_AND_FAILURE_DISPOSITION
gpu_execution_required=false
model_execution_required=false
prompt_change_permitted=false in the audit slice
new_authorization_permitted=false in the audit slice
```

The audit must bind:

- evidence archive SHA-256;
- all evidence-member hashes;
- notebook and authorization identities;
- request and cleanup counts;
- aggregate metrics;
- exact failed case IDs;
- exact reconstructed action and result hashes;
- privacy controls;
- the consumed authorization state;
- blocked cache and full-benchmark claims.

A separate later remediation may address:

```text
formatted integer normalization
named key-value field binding
```

That remediation must be measured against the full frozen diagnostic set and separately authorized.

---

# 11. Certificate Decision Record

```text
certificate_id=AURAGATEWAY-LOCAL-ABC-SFRC-0003
subject=reconcile-balance action-extraction canary v1
classification=CERTIFIED_FAILED_DIAGNOSTIC_WITH_CLEAN_HARNESS
model_requests_sent=12
authorized_requests_completed=12
semantic_failures=2
infrastructure_failures=0
schema_validity=12/12
operand_accuracy=10/12
final_answer_accuracy=10/12
cleanup=CLEAN
privacy_boundary=PASSED
authorization_consumed=YES
same_authorization_rerun=PROHIBITED
cache_claims=NOT_PERMITTED
full_measured_execution=NOT_AUTHORIZED
required_next_gate=IMMUTABLE_EVIDENCE_AUDIT_AND_FAILURE_DISPOSITION
```

---

# 12. Issuer Statement

This certificate was prepared by an AI reliability architecture assistant from the frozen evidence archive and repository-bound contracts.

The reasoning is reproducible from:

1. the evidence archive SHA-256;
2. the final report;
3. the checkpoint;
4. the evaluation report;
5. the 12-entry request ledger;
6. the fixed case manifest;
7. the deterministic action and result fingerprint contracts.

The certificate deliberately distinguishes observed facts, hash-resolved reconstruction, derived conclusions, and prohibited claims.
