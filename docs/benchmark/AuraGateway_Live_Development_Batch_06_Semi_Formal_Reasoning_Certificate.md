# AuraGateway Batch 06 — Semi-Formal Reasoning Certificate

**Certificate ID:** `AURAGATEWAY-SFRC-B06-001`  
**Project:** AuraGateway v2  
**Subject:** Condition C turn-3 Groq request rejection  
**Evidence status:** `FAILED_VERIFIED`  
**Reasoning status:** `CAUSE_NOT_ESTABLISHED`  
**Scope:** Static code-path reasoning plus recorded Batch 06 execution evidence  
**Excluded:** Raw provider outputs, protected prompt contents, secret material, unapproved reruns

---

## 1. Purpose

This certificate records the evidence, premises, execution trace, competing hypotheses, eliminations, and bounded conclusion for the Batch 06 failure.

It is not a root-cause declaration. Its purpose is to prevent the project from prematurely fixing the wrong layer.

---

## 2. Definitions

**D1 — Deterministic request-content defect**  
A defect in the provider-visible request content or fixed request parameters that should reproduce when the same request is submitted under materially equivalent conditions.

**D2 — Provider-visible request equivalence**  
Two attempts are provider-visible equivalent when their system prompt bytes, user prompt bytes, model, completion-token budget, temperature, streaming mode, storage mode, and reasoning effort are identical.

**D3 — Request rejection**  
The provider rejects a submitted request before returning a usable assistant response.

**D4 — Response validation failure**  
The provider returns a response, but the local adapter cannot validate or safely consume the response envelope.

**D5 — Transient provider/backend rejection**  
A non-deterministic provider-side or transport-side failure that may reject one instance of a valid request while accepting a later equivalent instance.

**D6 — Prefix-cache state anomaly**  
A provider-side failure associated with the creation, reuse, routing, or invalidation of an exact-prefix cache entry.

**D7 — Verified failed batch**  
A batch whose journal and evidence reconcile successfully, but whose acceptance receipt correctly fails.

**D8 — Cause established**  
A causal explanation supported by direct evidence or a controlled differential experiment that rules out credible alternatives.

---

## 3. Evidence Inventory

### E1 — Batch-level execution result

- Batch run exit code: `0`
- Verification exit code: `0`
- Receipt exit code: `1`
- Terminal records: `3`
- Completed runs: `2`
- Provider-error runs: `1`
- Attempts/provider calls: `11`
- Retries authorized: `0`
- Safety aborts: `0`
- Budget failures: `0`
- Structured-output failures: `0`
- Citation-scope failures: `0`

### E2 — Failed trajectory

| Field | Recorded value |
|---|---|
| Run | `run-functional-ep-func-001-r03-condition-c` |
| Condition | `condition_c` |
| Failed turn | `3` |
| Completed turns | `2` |
| Attempt index | `1` |
| Route reason | `warm_cache_affinity` |
| Provider status | `failed` |
| Response certainty | `definite_failure` |
| Retry authorized | `False` |
| Public provider error | `PROVIDER_RESPONSE_INVALID` |
| Terminal failure code | `NONRETRYABLE_PROVIDER_FAILURE` |

### E3 — Protected metadata-safe diagnostic

| Field | Recorded value |
|---|---|
| Diagnostic family | `request_rejected` |
| Exception class | `BadRequestError` |
| HTTP status | `400` |
| Provider error type | `invalid_request_error` |
| Provider error code | unavailable/unrecognised |
| Provider error parameter | unavailable/unrecognised |
| Retryable | `False` |
| Response metadata | absent because no usable response existed |

### E4 — Provider-visible prompt comparison

#### Condition C turn 3

- Prompt bytes: `8109`
- System prompt SHA-256:  
  `920108586c416aa130404de114d144aca3586a212fb87966db5ec01a2ed3bbcd`
- User prompt SHA-256:  
  `0afb78b0bdec5243e8f3cf15a9166cb670827e04df6a34ccf97700991a1e0155`
- Outcome: HTTP 400 request rejection

#### Condition B turn 3

- Prompt bytes: `8109`
- System prompt SHA-256:  
  `920108586c416aa130404de114d144aca3586a212fb87966db5ec01a2ed3bbcd`
- User prompt SHA-256:  
  `0afb78b0bdec5243e8f3cf15a9166cb670827e04df6a34ccf97700991a1e0155`
- Outcome: success
- Recorded input tokens: `1884`

### E5 — Larger successful requests

| Condition | Turn | Prompt bytes | Recorded input tokens | Outcome |
|---|---:|---:|---:|---|
| A | 3 | 8310 | 1946 | succeeded |
| A | 4 | 8846 | 2074 | succeeded |
| B | 4 | 8465 | 1957 | succeeded |

### E6 — Relevant implementation behavior

1. Conditions B and C use the same provider-facing prompt arrangement:
   - stable content in the system message;
   - volatile content in the user message.
2. The Groq adapter submits:
   - system message;
   - user message;
   - fixed model;
   - fixed completion-token budget;
   - `temperature=0.0`;
   - `stream=False`;
   - `store=False`;
   - `reasoning_effort="low"`.
3. `route_reason`, cache namespace, logical request identifier, fixture identifier, and prefix HMAC fingerprint are local harness metadata and are not submitted as Groq request parameters.
4. The failure occurred before a usable provider response existed.
5. The adapter currently maps recognised 4xx request rejection into a public error named `PROVIDER_RESPONSE_INVALID`, which does not precisely describe the recorded diagnostic family.

---

## 4. Premises

**P1.** Condition C turn 3 and Condition B turn 3 had identical system-prompt and user-prompt SHA-256 values.

**P2.** Both attempts had the same total prompt byte count: `8109`.

**P3.** The relevant provider-facing generation parameters are fixed by the adapter.

**P4.** Condition C turn 3 was rejected with HTTP 400 before a usable assistant response existed.

**P5.** Condition B turn 3 later succeeded with the equivalent provider-visible request.

**P6.** Requests larger than Condition C turn 3 succeeded.

**P7.** The local `warm_cache_affinity` label was not sent to Groq.

**P8.** The execution was sequential and no application-level retry was authorized for the failed attempt.

**P9.** Batch evidence reconciled successfully, and the receipt rejected acceptance because only two runs completed.

**P10.** No raw provider error message is available in the public or metadata-safe diagnostic evidence.

---

## 5. Execution and Data-Flow Trace

### T1 — Condition C turn 1

1. AuraGateway builds the stable system prompt.
2. AuraGateway builds the volatile user prompt for turn 1.
3. The adapter submits the request.
4. Groq returns a usable response.
5. The protected output is retained locally.
6. The public attempt record is marked successful.
7. The assistant output becomes part of later volatile conversation history.

**Result:** succeeded.

### T2 — Condition C turn 2

1. AuraGateway reuses the same stable system prompt.
2. AuraGateway builds turn-2 volatile content containing prior history.
3. The adapter submits the request.
4. Groq returns a usable response.
5. The output is retained and included in later history.

**Result:** succeeded.

### T3 — Condition C turn 3

1. AuraGateway reuses the same stable system prompt.
2. AuraGateway builds turn-3 volatile content containing turns 1 and 2.
3. Prompt summary:
   - `8109` bytes;
   - system hash `92010858...`;
   - user hash `0afb78b0...`.
4. The adapter submits the request.
5. Groq raises `BadRequestError`.
6. HTTP status is `400`.
7. Provider type is `invalid_request_error`.
8. No usable assistant response exists.
9. The adapter records a metadata-safe `request_rejected` diagnostic.
10. The failure is classified as definite and non-retryable.
11. AuraGateway writes one failed attempt record.
12. AuraGateway terminates Condition C with `provider_error`.

**Result:** failed before response handling.

### T4 — Conditions A and B

1. Condition A completes four turns.
2. Condition B uses the same stable system prompt shape as Condition C.
3. Condition B turn 3 has the same prompt hashes and byte count as failed Condition C turn 3.
4. Groq accepts Condition B turn 3.
5. Condition B completes all four turns.

**Result:** equivalent visible request later succeeded.

---

## 6. Formal Claims

### Claim C1 — The failure was a request rejection, not a response validation failure

**Evidence:** E3 and T3.

A `BadRequestError` with HTTP 400 occurred before any response envelope was available for typed response validation.

**Status:** PROVEN within recorded evidence.

---

### Claim C2 — A deterministic prompt-content defect is not supported

By P1, P2, P3, and P5, the equivalent provider-visible request later succeeded.

If the system prompt, user prompt, or fixed generation parameters were deterministically invalid, the later equivalent request should also have been rejected under ordinary deterministic validation.

**Status:** STRONGLY REFUTED as the leading explanation.

---

### Claim C3 — Prompt size or context-length exhaustion is not supported

By P6, larger requests succeeded. Condition B turn 3 also succeeded with the same prompt and recorded only `1884` input tokens.

**Status:** STRONGLY REFUTED.

---

### Claim C4 — Malformed accumulated conversation history is not supported

The user-prompt hash for C3 and B3 is identical. The volatile prompt contains the accumulated conversation history. Therefore the histories included in those prompts were byte-equivalent.

**Status:** STRONGLY REFUTED.

---

### Claim C5 — The local route label did not directly cause the provider rejection

By P7, `warm_cache_affinity` was not submitted to Groq.

**Status:** PROVEN for direct causation.

This does not rule out a provider-side state correlated with repeated exact-prefix calls.

---

### Claim C6 — The current public error taxonomy is semantically imprecise

The recorded family is `request_rejected`, while the public code says `PROVIDER_RESPONSE_INVALID`.

A rejected request and an invalid returned response are distinct failure boundaries.

**Status:** PROVEN.

---

### Claim C7 — A transient provider/backend rejection is consistent with all current evidence

One instance of an equivalent request failed while a later instance succeeded. Hidden provider-side state, request admission, backend routing, transport state, or internal error misclassification can explain this pattern.

**Status:** SUPPORTED, not proven.

---

### Claim C8 — A provider prefix-cache state anomaly is plausible

Condition C was the first repeated stable-prefix sequence:

- C1 succeeded;
- C2 succeeded;
- C3 failed;
- later B1–B4 with the same stable-prefix construction succeeded.

A temporary cache creation, lookup, invalidation, or backend-affinity inconsistency could produce this timing pattern.

**Status:** PLAUSIBLE, not proven.

---

### Claim C9 — Conditions B and C are not fully isolated at the provider boundary

The current adapter submits the same visible prompt construction and model for B and C. C-specific affinity is represented as local telemetry rather than an explicit provider routing control.

Therefore B and C can share provider-side exact-prefix state.

**Status:** SUPPORTED by the current request path.

---

## 7. Alternative Hypothesis Matrix

| Hypothesis | Supporting evidence | Contradicting evidence | Assessment |
|---|---|---|---|
| H1: Prompt too large | Failure occurred on a later turn | Larger A3, A4, and B4 requests succeeded; B3 equivalent request succeeded | Strongly refuted |
| H2: Context length exceeded | Later-turn prompt contains history | Equivalent B3 recorded 1884 tokens and succeeded | Strongly refuted |
| H3: Malformed conversation history | C3 includes prior assistant outputs | B3 user hash is identical and succeeded | Strongly refuted |
| H4: Ordinary deterministic content rejection | Provider returned HTTP 400 | Equivalent B3 request succeeded | Weak |
| H5: Local `warm_cache_affinity` value rejected | Failure carried that route label | Route label is not sent to provider | Direct causation refuted |
| H6: Local request ID/cache namespace/HMAC caused failure | Values differ locally | They are not submitted as provider parameters | Direct causation refuted |
| H7: SDK serialized one call incorrectly | Single call failed | Same simple synchronous call path worked ten times; no direct wire evidence | Possible, low support |
| H8: Transient provider/backend rejection | Equivalent request later succeeded | Exact internal provider state unavailable | Most supported class |
| H9: Prefix-cache state anomaly | Failure occurred on third repeated stable-prefix call; later equivalent calls succeeded | No provider cache trace or direct cache error code | Plausible |
| H10: Hidden transport/backend difference | Connection, replica, region, or provider request state may differ | Not observable in current evidence | Possible |
| H11: Undocumented sequencing/admission rule | Failure followed rapid repeated-prefix requests | Very low call volume; provider returned 400 rather than 429 | Possible, lower support |

---

## 8. Counterfactual Checks

### CF1 — Deterministic invalid request

**Expected evidence if true:**  
The equivalent B3 request should also fail.

**Observed:**  
B3 succeeded.

**Conclusion:**  
Counterfactual not satisfied.

### CF2 — Byte-size threshold

**Expected evidence if true:**  
Requests exceeding `8109` bytes should fail consistently.

**Observed:**  
Requests of `8310`, `8465`, and `8846` bytes succeeded.

**Conclusion:**  
Counterfactual not satisfied.

### CF3 — Local route label causes provider rejection

**Expected evidence if true:**  
The route label must reach the provider request boundary.

**Observed:**  
It remains local telemetry.

**Conclusion:**  
Counterfactual impossible under the current call path.

### CF4 — Provider-state-dependent failure

**Expected evidence if true:**  
Equivalent requests may produce different outcomes at different times or sequence positions.

**Observed:**  
C3 failed and later equivalent B3 succeeded.

**Conclusion:**  
Counterfactual is satisfied, but multiple provider-state explanations remain.

---

## 9. Ranked Causal Assessment

### Rank 1 — Transient provider/backend rejection misclassified as HTTP 400

**Confidence:** Medium.

This is the broadest explanation consistent with all evidence and requires the fewest unsupported assumptions.

Potential mechanisms include:

- transient request-admission fault;
- backend replica inconsistency;
- tokenizer or request-translation service instability;
- internal provider error surfaced as `invalid_request_error`;
- transport or connection-state anomaly.

### Rank 2 — Provider exact-prefix cache state or routing anomaly

**Confidence:** Low to medium.

The timing is suggestive because C3 was the third request in the first repeated stable-prefix sequence. However, no direct cache trace, cache-hit field, cache error code, or provider routing identifier proves this.

### Rank 3 — Undocumented provider sequencing or admission behavior

**Confidence:** Low.

Repeated exact-prefix or reasoning requests could trigger a provider-side rule, but the volume was small and the returned status was not a conventional rate-limit response.

### Rank 4 — SDK or local transport serialization anomaly

**Confidence:** Low.

Possible, but no direct evidence distinguishes it from provider/backend state.

---

## 10. Formal Conclusion

From D1–D8, P1–P10, T1–T4, C1–C9, and CF1–CF4:

1. Batch 06 is a **verified failed batch**.
2. The failed event was a **provider request rejection**, not a response-schema failure.
3. A deterministic prompt-content defect, context-length failure, malformed history, prompt-size threshold, or direct effect from the local route label is not supported.
4. The evidence supports a broader **provider-state-dependent or transient rejection class**.
5. A provider exact-prefix cache anomaly is a credible sub-hypothesis, but it is not established.
6. The exact causal mechanism remains unresolved because the provider supplied no recognised safe error code or parameter, and no controlled replay matrix has been executed.
7. Conditions B and C are not fully isolated at the provider boundary because they can submit equivalent visible requests and share provider-side exact-prefix state.

### Machine-readable verdict

```yaml
certificate_id: AURAGATEWAY-SFRC-B06-001
batch_status: FAILED_VERIFIED
failure_boundary: PROVIDER_REQUEST_REJECTED
deterministic_prompt_defect_supported: false
context_length_failure_supported: false
malformed_history_supported: false
direct_route_label_causation_supported: false
transient_provider_state_supported: true
prefix_cache_anomaly_status: PLAUSIBLE_NOT_PROVEN
exact_root_cause: NOT_ESTABLISHED
implementation_fix_selected: false
rerun_authorized: false
```

---

## 11. Claims Explicitly Not Made

This certificate does not claim:

- that Groq has a confirmed cache bug;
- that AuraGateway cache affinity caused the rejection;
- that provider caching occurred on any specific attempt;
- that Condition C improves cost, latency, or quality;
- that B and C are experimentally independent;
- that Batch 06 produced a valid A/B/C comparison;
- that a production fix has been identified;
- that a retry would have succeeded;
- that the system is production-ready;
- that the public error taxonomy defect caused the provider rejection.

---

## 12. Evidence Needed to Establish Cause

A future controlled diagnostic authorization should distinguish among the remaining hypotheses without mutating Batch 06 evidence.

### Experiment X1 — Isolated identical request

Submit the equivalent logical C3 request as isolated, spaced one-off attempts.

**Diagnostic value:** distinguishes deterministic request invalidity from intermittent provider behavior.

### Experiment X2 — Sequence replay

Compare:

- stable-prefix turns 1 → 2 → 3;
- equivalent stable-prefix turns 1 → 2 → 3 under another local condition label.

**Diagnostic value:** identifies whether failure follows provider-visible sequence shape or local condition identity.

### Experiment X3 — Controlled spacing

Compare the same sequence with bounded delays.

**Diagnostic value:** tests rapid-prefix-reuse, cache-warming, or request-admission hypotheses.

### Experiment X4 — Order reversal

Run B first and C later under a fresh authorization.

**Diagnostic value:**

- first stable-prefix sequence fails: position/cold-state hypothesis strengthened;
- C fails regardless of position: hidden C-specific harness difference strengthened;
- failures move randomly: transient provider instability strengthened;
- no failure: historical transient event remains strongest.

### Experiment X5 — Safe transport metadata

Retain only:

- request timestamp bucket;
- SDK version;
- message count;
- system/user/total byte counts;
- explicit parameter-presence flags;
- provider request-ID hash;
- connection-reuse flag where safely observable;
- no prompt text;
- no raw provider error text;
- no secret-bearing headers.

**Diagnostic value:** tests whether requests equivalent at the logical boundary differed at the transport boundary.

---

## 13. Certificate Validity Boundary

This certificate remains valid only for the recorded Batch 06 evidence and the inspected implementation path.

It must be revised if any of the following emerges:

- the C3 and B3 provider parameter sets were not identical;
- the recorded prompt hashes were computed from a representation different from the submitted strings;
- hidden C-specific request fields are discovered;
- the Groq SDK transformed C3 differently;
- a provider request code or parameter identifies a deterministic request defect;
- controlled replay produces a stable alternative explanation.

---

## 14. Final Status

**Reasoned result:** `CAUSE_NOT_ESTABLISHED`  
**Best-supported causal class:** `TRANSIENT_OR_PROVIDER_STATE_DEPENDENT_REQUEST_REJECTION`  
**Specific cache claim:** `PLAUSIBLE_NOT_PROVEN`  
**Engineering decision:** preserve Batch 06 unchanged; do not select a fix until the remaining causal classes are experimentally separated.
