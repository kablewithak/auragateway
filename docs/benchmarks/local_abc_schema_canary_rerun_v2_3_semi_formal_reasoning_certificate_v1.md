# Semi-Formal Reasoning Certificate

## AuraGateway Local A/B/C Schema-Constrained Quality/Cache Canary Rerun v2.3

**Certificate ID:** `auragateway-local-abc-sfrc-0001`  
**Certificate version:** `1.0.0`  
**Status:** `CERTIFIED_FAILED_DIAGNOSTIC`  
**Evidence class:** Kaggle-measured, synthetic, controlled  
**Formal proof claimed:** False  
**Customer data used:** False  
**External spend:** R0 / $0  
**GPU authorization created by this certificate:** None

---

## 1. Purpose

This certificate answers one bounded question:

> What does the v2.3 canary evidence prove about the failure, which alternative
> explanations are refuted, and what decision boundary may the ADR address?

The structure adapts the premise → trace → divergence → alternative-hypothesis
→ formal-conclusion method from *Agentic Code Reasoning* by Shubham Ugare and
Satish Chandra. It is an inspectable reasoning artifact, not a machine-checked
formal proof.

---

## 2. Evidence Bindings

| Field | Bound value |
|---|---|
| Evidence archive | `auragateway-schema-constrained-quality-cache-canary-rerun-v2-evidence.zip` |
| Archive SHA-256 | `38dfb3e727b5234e9db510e0c4735150e5721b479908c69fec4d4c8e004059f1` |
| Repository commit | `5d8170b5f33f9bff07a3f6c0db3f90b5399a1bae` |
| Run ID | `auragateway-schema-canary-rerun-v2-bf55bf4de546` |
| Rerun authorization fingerprint | `7e8f9529cdf43118a09f5c6c9512f8729447a506b3a61cd303c6e09a652dbd66` |
| Failed predecessor audit fingerprint | `45712ac7ab42c17bc949dc374dd1e4114ab408657b54d36509c0d241a5f74019` |
| Preserved scope fingerprint | `d1563d346138f10c4701492a2c1ddc7bd02bb0c5c937221b36c916361e348c64` |
| Token-normalization policy fingerprint | `9b16866de747d67f41e4289d6f5fc9e7398da0054ee052dcc9371c5585954830` |
| Schedule SHA-256 | `fcae45007e883875dc29acdb4388ff20458d6ab5851331f005d09b97cec44ab8` |
| Report SHA-256 | `351128671b40beda9163415a09d006ea215d2ff84b2dce89c4e5a15666c4e1a5` |
| Ledger SHA-256 | `8005e62f7ca807fd65ccca0b3e3f29fcde26e2c6853d77042d6a719e243592cc` |
| Checkpoint SHA-256 | `607520a7f36dd1a2da67cf5afb6571d3d21ea2a3ea37bf6ef730560bb6e800a2` |
| Raw prompts retained | `false` |
| Raw outputs retained | `false` |

---

## 3. Definitions

**D1 — Canary pass.** The bounded canary passes only if all three two-turn
trajectories complete, all six requests pass quality, schema, telemetry, cache,
route, and zero-failure gates, and cleanup is clean.

**D2 — Observed state.** A request is observed only when a ledger record exists.
Unexecuted requests are `NOT_OBSERVED`; they cannot be labeled passed, failed,
zero-cache, or positive-cache.

**D3 — Failure boundary.** A harness defect is supported when repository
planning, validation, routing, telemetry, or scoring diverges from the frozen
contract. A model-output semantic failure is supported when those boundaries
pass but the deterministic expected answer does not match.

**D4 — Authorization consumption.** The rerun authorization is consumed once
real canary model requests execute. It cannot authorize another run.

---

## 4. Premises

**P1.** Repository, audit, authorization, token-normalization, case-manifest,
model, and runtime bindings qualified.

**P2.** The frozen scope was three Condition-C trajectories, six requests,
`worker_1 → worker_1`, full worker restart before every trajectory, no retries,
and no replacement trajectories.

**P3.** Incident-severity turn 1 passed exact output quality, schema, telemetry,
route, and cold-cache gates. Planned, API, and metric prompt-token counts were
all `282`.

**P4.** Incident-severity turn 2 passed exact output quality, schema, telemetry,
route, and positive-cache gates. It observed `192` cached tokens from `205`
eligible shared-prefix tokens, a bounded reuse ratio of `93.6585%`.

**P5.** Payment-reconciliation turn 1 passed HTTP, JSON parsing, exact key set,
case ID, turn index, confidence, schema, telemetry, route, and cold-cache gates.

**P6.** Payment-reconciliation turn 1 failed only exact-answer matching and
emitted `OUTPUT_ANSWER_MISMATCH`.

**P7.** The zero-failure policy aborted after the third completed request.
Payment-reconciliation turn 2 and both data-sharing-policy turns were not
executed.

**P8.** Both workers exited cleanly and ports `8001` and `8002` closed.

---

## 5. Execution Trace

| Step | Boundary | Outcome | Grounded observation |
|---:|---|---|---|
| 1 | Source and authorization preflight | Passed | Exact repository, evidence, model, runtime, and scope bindings qualified. |
| 2 | Incident-severity turn 1 | Passed | `planned=282`, `api=282`, `metric=282`, `cached=0`. |
| 3 | Incident-severity turn 2 | Passed | `planned=290`, `api=290`, `metric=290`, `cached=192`, `eligible_shared_prefix=205`. |
| 4 | Payment-reconciliation turn 1 | Failed quality only | `planned=289`, `api=289`, `metric=289`, `cached=0`, `OUTPUT_ANSWER_MISMATCH`. |
| 5 | Zero-failure abort | Aborted as designed | No retry or replacement trajectory occurred. |
| 6 | Worker cleanup | Clean | Both processes exited and both ports closed. |

---

## 6. Divergence Claims

**C1 — High confidence.** The prior rendered-token counting defect is remediated
for all three observed requests.

Derived from: `P1`, `P3`, `P4`, `P5`.

**C2 — High confidence.** Positive same-worker turn-two cache reuse is qualified
for the incident-severity trajectory only.

Derived from: `P4`.

**C3 — High confidence.** The terminal failure occurred at the model-output
semantic answer boundary after the observed harness boundaries passed.

Derived from: `P5`, `P6`.

**C4 — Medium confidence.** The evidence is consistent with insufficient
arithmetic or instruction-execution capability under the pinned model and frozen
prompt contract. It does not expose the model's internal causal mechanism, so it
cannot distinguish arithmetic computation failure from another internal semantic
failure.

Derived from: `P5`, `P6`.

**C5 — High confidence.** Payment-reconciliation turn 2 and both
data-sharing-policy turns are `NOT_OBSERVED`.

Derived from: `P7`.

**C6 — High confidence.** The six-request canary failed under its frozen
all-or-nothing acceptance contract.

Derived from: `P2`, `P6`, `P7`.

**C7 — High confidence.** The v2 rerun authorization is consumed and cannot be
reused.

Derived from: `P2`, `P7`.

**C8 — High confidence.** The full 72-trajectory measured benchmark remains
blocked.

Derived from: `P7`, `P8`.

---

## 7. Alternative-Hypothesis Check

| Hypothesis | Verdict | Evidence |
|---|---|---|
| H1: Token normalization still failed. | Refuted for observed requests | Planned, API, and metric counts match for all three observed requests. |
| H2: JSON schema or envelope failed. | Refuted | Payment turn 1 passed parsing, key-set, identity, confidence, no-extra-text, and schema checks. |
| H3: Cache telemetry caused the payment failure. | Refuted | Telemetry and cold-cache gates passed; failure code was `OUTPUT_ANSWER_MISMATCH`. |
| H4: Route or worker lifecycle failed. | Refuted | Authorized worker was realized and cleanup was clean. |
| H5: The harness hid or retried the bad result. | Refuted | Failed metadata was retained; zero-failure abort occurred without retries or replacements. |
| H6: The pinned model and frozen prompt contract did not reliably satisfy the mixed semantic canary. | Supported | The arithmetic case failed exact-answer matching after all observed harness gates passed. |
| H7: Cache-aware routing as a whole failed. | Not supported | One complete trajectory showed positive cache reuse; remaining cache observations were not executed. |

---

## 8. Counterexample

A claim that the mixed six-request canary qualified requires every request to
pass. Payment-reconciliation turn 1 is a counterexample:

```text
case_id=payment-reconciliation
turn_index=1
expected_answer=1450
exact_answer_match=false
failure_code=OUTPUT_ANSWER_MISMATCH
output_text_sha256=c7cd9dd704ec1660a8085b2561e7c9101b234ca2ad523d9675272db03177b5bf
```

The archive did not retain raw model output. This certificate preserves the hash
and failure classification rather than promoting reconstructed raw output into
the evidence lineage.

Therefore, at least one required request produced a semantically incorrect
answer, and the all-six canary cannot pass.

---

## 9. Formal Conclusion

1. By `D1`, all six requests must pass.
2. By `P6`, payment-reconciliation turn 1 failed exact-answer matching.
3. By `P7`, execution aborted after three completed requests and three requests
   remained `NOT_OBSERVED`.
4. Therefore, the canary is `CERTIFIED_FAILED_DIAGNOSTIC`.
5. By `C1`, the original token-counting defect is not the terminal cause.
6. By `C3`, the terminal divergence is at the model-output semantic answer
   boundary.
7. By `C7`, the rerun authorization is consumed.
8. By `C8`, the full measured benchmark remains blocked.

**Answer:** The v2.3 canary did not qualify. The observed terminal failure is an
exact semantic answer mismatch under an otherwise passing observed harness path.

---

## 10. ADR Decision Boundary

The ADR must choose the next system boundary for deterministic arithmetic
reliability without rewriting this failed evidence.

### Admissible option A — Typed deterministic action realization

The model emits validated arithmetic intent and operands. Repository code
performs the calculation and returns a typed result.

This is a new system boundary and requires:

- a typed action schema;
- operand validation;
- deterministic calculation;
- refusal/error states;
- separate fixed cases and baseline;
- new authorization;
- a new evidence lineage.

### Admissible option B — New model-capability binding

Bind a different model and run a newly authorized capability experiment.

This requires:

- a documented model-selection criterion;
- exact model and tokenizer revisions;
- cost and latency implications;
- unchanged hard-case expectations;
- new authorization;
- a new evidence lineage.

### Rejected options

- change the expected answer;
- remove the arithmetic case;
- weaken exact-answer scoring;
- add hidden retries;
- replace the failed trajectory;
- reuse the consumed authorization;
- run the full measured benchmark.

**This certificate does not choose between option A and option B.** That is the
ADR's responsibility.

---

## 11. Non-Claims

This certificate does not claim:

- payment-reconciliation turn 2 passed or failed;
- either data-sharing-policy turn passed or failed;
- all case types benefit from cache reuse;
- the pinned model is universally incapable of arithmetic;
- a larger model will solve the problem;
- deterministic action realization is implemented or validated;
- the 72-trajectory benchmark is authorized;
- the system is production-ready.

---

## 12. Next Safe Action

Review and approve this certificate. Then draft the ADR using only the
admissible decision boundary in Section 10.

Keep GPU execution off.

---

## 13. Machine-Readable Companion

The canonical JSON companion is:

```text
schema_canary_rerun_v2_3_semi_formal_reasoning_certificate_v1.json
SHA-256=ed2b7a204b168904dc48ce0b70e49d7a4121750f632fde1f370494f97b782303
```
