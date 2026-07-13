# AuraGateway Live Development Batch 06 — Closeout

**Batch:** `auragateway-live-development-batch-06`  
**Authorization:** `live-development-batch-06-auth-v1`  
**Status:** `FAILED_VERIFIED`  
**Acceptance:** Rejected as designed  
**Rerun:** Not authorized  
**Root cause:** Not established

---

## 1. Closeout decision

Batch 06 is preserved as immutable failed execution evidence.

The batch completed its bounded execution path and produced three terminal records. Evidence verification passed, but receipt acceptance failed because only two of the three authorized trajectories completed and one trajectory ended in a provider error.

This is a valid negative result, not an incomplete run.

---

## 2. Recorded outcome

| Measure | Value |
|---|---:|
| Selected runs | 3 |
| Terminal records | 3 |
| Attempt/provider-call records | 11 |
| Completed runs | 2 |
| Provider-error runs | 1 |
| Retries authorized | 0 |
| Safety aborts | 0 |
| Budget failures | 0 |
| Structured-output failures | 0 |
| Citation-scope failures | 0 |
| Total estimated cost | 1,635 micro-USD |

The failed trajectory was:

- run: `run-functional-ep-func-001-r03-condition-c`
- condition: `condition_c`
- turn: `3`
- completed turns before failure: `2`
- route reason: `warm_cache_affinity`
- provider status: `failed`
- response certainty: `definite_failure`
- retry authorized: `false`
- terminal status: `provider_error`
- terminal failure: `NONRETRYABLE_PROVIDER_FAILURE`

---

## 3. Failure boundary

The metadata-safe provider diagnostic recorded:

- family: `request_rejected`
- exception class: `BadRequestError`
- HTTP status: `400`
- provider error type: `invalid_request_error`
- retryable: `false`
- provider error code: unavailable or not allowlisted
- provider error parameter: unavailable or not allowlisted

The provider rejected the request before returning usable assistant content.

This was not a typed response-envelope validation failure.

---

## 4. Differential evidence

Condition C turn 3 and Condition B turn 3 had:

- identical prompt byte count: `8109`
- identical system-prompt SHA-256
- identical user-prompt SHA-256
- the same fixed provider-facing generation parameters

Condition C turn 3 was rejected. Condition B turn 3 later succeeded.

Larger requests also succeeded.

Therefore, the current evidence does not support the following as leading causes:

- deterministic invalid prompt content
- malformed accumulated conversation history
- prompt-size threshold
- context-length exhaustion
- direct rejection of the local `warm_cache_affinity` label

The best-supported causal class is a transient or hidden provider-state-dependent request rejection.

A provider exact-prefix cache-state anomaly remains plausible but unproven.

---

## 5. Evidence retained in Git

The following Batch 06 public evidence is expected to be committed:

- `data/evals/benchmark/live-development-v6/authorization.json`
- `data/evals/benchmark/live-development-v6/runtime_policy.json`
- `data/evals/benchmark/live-development-v6/journal.jsonl`
- `data/evals/benchmark/live-development-v6/run_records.json`
- `data/evals/benchmark/live-development-v6/report.json`
- `data/evals/benchmark/live-development-v6/manifest.json`

The following implementation and validation assets are expected to be committed:

- `src/auragateway/benchmark/execution.py`
- `src/auragateway/benchmark/execution_runner.py`
- `src/auragateway/benchmark/live_output_adapter.py`
- `tests/unit/benchmark/test_live_development_batch_06.py`
- `docs/benchmark/AuraGateway_Live_Development_Batch_06_Authorization.md`
- `docs/benchmark/AuraGateway_Live_Development_Batch_06_Closeout.md`
- `docs/benchmark/AuraGateway_Live_Development_Batch_06_Semi_Formal_Reasoning_Certificate.md`

---

## 6. Protected local evidence

The following protected artifacts remain local and must not be committed, pasted, or included in pull-request content:

- `.local/benchmark/live-development-v6/protected_outputs.jsonl`
- `.local/benchmark/live-development-v6/provider_failure_diagnostics.jsonl`
- `.local/benchmark/live-development-v6/provider_raw_outputs.jsonl`

Only names, sizes, hashes, and allowlisted metadata may be surfaced when needed.

---

## 7. Acceptance and non-claims

Batch 06 does not provide an accepted A/B/C comparison.

It does not establish:

- a Groq prefix-cache defect
- cache-affinity causation
- cache savings
- latency improvement
- cost improvement
- quality improvement
- benchmark superiority
- production readiness

It does establish that:

- the C-first trajectory was genuinely attempted
- two C turns completed before request rejection
- A and B completed
- the request rejection was retained safely
- no unsafe retry occurred
- the batch remained auditable
- receipt acceptance prevented a false success claim

---

## 8. Next authorized engineering slice

After this branch is merged and cleaned up, use a separate branch for:

1. provider request-rejection taxonomy correction
2. metadata-safe request-rejection diagnostic hardening
3. regression tests for recognised and unknown 400-class failures
4. a separately reviewed controlled diagnostic authorization

Do not authorize another provider execution merely to seek a successful outcome.

A future execution must have a predeclared diagnostic question that separates transient provider behavior, sequence position, stable-prefix reuse, and hidden provider-state hypotheses.

---

## 9. Final status

```yaml
batch_status: FAILED_VERIFIED
receipt_status: REJECTED_AS_DESIGNED
failure_boundary: PROVIDER_REQUEST_REJECTED
exact_root_cause: NOT_ESTABLISHED
best_supported_causal_class: TRANSIENT_OR_PROVIDER_STATE_DEPENDENT
prefix_cache_anomaly_status: PLAUSIBLE_NOT_PROVEN
rerun_authorized: false
protected_evidence_committable: false
next_action: MERGE_CLOSEOUT_THEN_HARDEN_DIAGNOSTICS
```
