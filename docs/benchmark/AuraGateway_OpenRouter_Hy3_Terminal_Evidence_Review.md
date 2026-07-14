# AuraGateway OpenRouter Hy3 Terminal Evidence Review
## Capability Probe Closeout, Claim Gate, and Continuity Decision

| Field | Value |
|---|---|
| Review ID | `openrouter-hy3-terminal-evidence-review-v1` |
| Status | Terminal |
| Provider boundary | OpenRouter |
| Requested model | `tencent/hy3:free` |
| Telemetry authority | OpenRouter-normalized usage |
| Execution source commit | `8a514458275ae6c1757e9f464c724312996a1ce6` |
| Sanitized closeout merge | `00d0712` |
| Closeout result | `openrouter-hy3-capability-probe-closeout-v1/closeout_result.json` |
| Final decision | Capability path closed; pilot and benchmark not authorized |

---

## 1. Review Question

Did the separately authorized OpenRouter `tencent/hy3:free` capability probe produce enough
trustworthy live evidence to:

1. confirm a successful Hy3 response path;
2. observe numeric cache telemetry;
3. observe controlled cache use; and
4. promote to a separate A/B/C pilot-authorization review?

## 2. Answer

No.

The probe reached OpenRouter once on the cold logical call and returned HTTP `401` before any
successful completion. The runner classified the response as
`PROVIDER_AUTHENTICATION_FAILED`, prohibited retry, skipped generation metadata and the warm call,
consumed the authorization, and produced a terminal receipt.

```text
terminal_outcome: closed_terminal_provider_failure
failure_stage: pre_inference_authentication
attempt_count: 1
provider_success_count: 0
retained_success_count: 0
replacement_count: 0
cold_call_attempted: true
warm_call_attempted: false
generation_metadata_requested: false
numeric_cache_telemetry_observed: false
controlled_cache_use_observed: false
route_identity_observed: false
comparison_eligible: false
pilot_authorized: false
retained_benchmark_authorized: false
authorization_consumed: true
resume_permitted: false
rerun_permitted: false
```

The capability gate did not pass.

---

## 3. Evidence Lineage

The extension used a staged irreversible-action boundary:

```text
1. Identifiability review
2. Generic OpenRouter adapter dry run
3. Capability authorization review
4. Exhaustive bounded state-model validation
5. One-time authorization activation
6. Protected prompt-bundle preparation
7. Metadata-only key and route preflight
8. Execution-runner implementation and merge
9. One live cold attempt
10. Protected terminal receipt
11. Sanitized capability closeout
12. Terminal evidence review
```

The live execution occurred only after the execution runner was merged to clean `main`.

## 4. Sanitized Source Evidence

The terminal review is grounded in:

```text
data/evals/benchmark/openrouter-hy3-capability-probe-closeout-v1/closeout_result.json
data/evals/benchmark/openrouter-hy3-capability-probe-closeout-v1/closeout_manifest.json
data/evals/benchmark/openrouter-hy3-capability-probe-closeout-v1/closeout_policy.json
docs/benchmark/AuraGateway_OpenRouter_Hy3_Capability_Probe_Closeout.md
docs/adr/openrouter-hy3-capability-probe-closeout.md
```

Protected local evidence remains outside Git:

```text
terminal receipt
attempt journal
raw response record
prompt bundle
preflight receipt
```

The public closeout binds those artifacts through hashes and byte counts without publishing their
sensitive contents.

---

## 5. Exact Terminal Observation

```text
logical call: cold_probe
attempt number: 1
response kind: completion
HTTP status: 401
provider error code: 401
safe error code: PROVIDER_AUTHENTICATION_FAILED
provider error message: Missing Authentication header
retry permitted: false
provider successes before close: 0
```

The successful-response path was never reached. Therefore:

```text
completion content validation: not reached
generation ID: unavailable
generation metadata: not requested
resolved model: unavailable
resolved upstream provider: unavailable
session reconciliation: unavailable
prompt tokens: unavailable
cached tokens: unavailable
cache-write tokens: unavailable
cache discount: unavailable
```

---

## 6. Authentication Root-Cause Boundary

The response proves that OpenRouter rejected authentication for the live completion request. It does
not prove why.

Potential explanations that remain unresolved include:

```text
credential validity or revocation
credential entry mismatch between preflight and execution
truncation or copy error
surrounding whitespace
header delivery through the exact live request
account-side or gateway-side authentication behavior
another authentication factor
```

A post hoc, zero-network diagnostic established:

```text
merged urllib backend can construct Authorization header: true
authorization scheme: Bearer
fixture credential used: true
real credential value used: false
system proxy entries detected: 0
network requests performed by diagnostic: 0
```

That diagnostic is regression evidence for the local code path. It is not evidence of what
OpenRouter received during the consumed live attempt.

The review therefore preserves:

```text
credential_continuity_proven: false
authorization_header_delivery_proven: false
root_cause_resolved: false
```

---

## 7. Retry and Terminal-Control Review

The failure was non-retryable under the frozen policy.

Authorized transient replacements were limited to:

```text
429
502
524
529
```

HTTP `401` required immediate closure.

Observed behavior:

```text
second cold attempt: not made
warm attempt: not made
manual resume: not permitted
rerun: not permitted
authorization consumption: recorded
terminal closeout: recorded
```

This is correct harness behavior even though it prevented a cache result.

---

## 8. Capability-Gate Decision

Promotion required all of the following:

```text
two retained successful responses
numeric cache-read or cache-write telemetry
controlled positive cache-use evidence
requested and resolved model reconciliation
upstream provider reconciliation
shared session identity
no unauthorized retry
verified protected evidence hashes
```

None of the live success-path requirements were reached.

Decision:

```text
capability gate: failed before successful inference
pilot authorization review: prohibited
A/B/C pilot: prohibited
retained benchmark: prohibited
comparison eligibility: false
```

---

## 9. Permitted Claims

The repository may claim:

> The one-time OpenRouter Hy3 capability probe closed on its first cold-call attempt after HTTP `401`
> with safe failure code `PROVIDER_AUTHENTICATION_FAILED`; no successful completion, generation
> metadata, route identity, or cache telemetry was obtained.

It may also claim:

```text
one network request was made
no transient replacement was used
no warm request was made
the authorization was consumed
resume and rerun are prohibited
the public closeout excludes raw payloads, prompts, and credentials
```

---

## 10. Non-Claims

The repository must not claim:

```text
Hy3 inference succeeded
Hy3 inference failed for a model-level reason
OpenRouter removed an Authorization header
credential validity was the exact root cause
privacy-compatible routing failed
the free route was unavailable
cache telemetry was absent from a successful Hy3 response
a cache hit or miss occurred
cached tokens were zero
cache write or cache read occurred
route affinity was observed
latency or cost improved
Condition C was tested
A/B/C comparison was completed
```

---

## 11. Relationship to the Groq Lineage

The two provider lineages closed at different points:

```text
Groq:
  successful model responses: yes
  required cache field: absent
  terminal category: successful inference with insufficient telemetry

OpenRouter/Hy3:
  successful model responses: no
  terminal response: HTTP 401
  terminal category: pre-inference authentication failure
```

The OpenRouter extension does not replace, repair, or invalidate the Groq result. Both remain
independently valid and immutable.

Combined conclusion:

> Neither provider lineage produced the trustworthy numeric cache evidence required to authorize the
> measured A/B/C benchmark.

---

## 12. Residual Harness Findings

The live failure exposed three future hardening requirements:

1. Retain a protected credential fingerprint during preflight and execution so credential continuity
   can be checked without retaining the key.
2. Retain non-sensitive proof that the authorization header was constructed for the exact live
   request, without recording the header value.
3. Reject a credential when `credential != credential.strip()` instead of validating the stripped
   value and transporting the original value.

These are future-lineage requirements. They do not authorize a rerun of this probe.

---

## 13. Privacy and Publication Review

Public evidence contains:

```text
safe status and error fields
attempt accounting
terminal outcome
artifact hashes
bounded residual gaps
claims and non-claims
```

Public evidence excludes:

```text
API key
Authorization header value
raw provider body
protected prompt
session identity
raw journal
customer data
PII
```

The result is eligible for static publication only as a sanitized terminal-failure case study.

---

## 14. Maturity Decision

Achieved:

```text
Production-shaped
Locally validated
Synthetic-data validated
Controlled-provider tested
Terminal closeout validated
```

Not achieved:

```text
Successful Hy3 inference
Numeric cache telemetry validation
Provider-specific cache benchmark validation
Customer-data testing
Deployment
Production readiness
```

---

## 15. Commercial Translation

### AI System Evaluation Audit

The proof asset demonstrates that a provider should not be selected for a cache-efficiency benchmark
until both authentication continuity and telemetry sufficiency are proven.

### Agent Harness Hardening Sprint

The proof asset demonstrates one-time authorization, bounded retry semantics, write-through evidence,
and terminal closure under external-call failure.

### AI Reliability Retainer

The residual gaps translate into recurring controls for credential drift, provider-contract drift,
and claim-boundary enforcement.

The sellable result is not a positive cache number. It is a defensible decision about what could and
could not be measured.

---

## 16. Final Decision

```text
terminal review: passed
capability path: closed
pilot: not authorized
retained benchmark: not authorized
runtime rerun: prohibited
next optional phase: static Hugging Face publication integration
```

The correct engineering behavior is to preserve the terminal result and continue only with sanitized
publication or a separately designed new provider lineage.
