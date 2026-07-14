# AuraGateway Provider Evidence Matrix
## Terminal Provider, Telemetry, and Claim Status

| Field | Value |
|---|---|
| Document version | 1.0.0 |
| Status | Terminal |
| Project | AuraGateway v2 |
| Governing PRD | `AuraGateway_v2_PRD_Cache_Aware_Agent_Runtime_Harness.md` 2.3.0 |
| Source checkpoint | `main` at `00d0712` before this continuity update |
| Purpose | Separate adapter capability, live provider evidence, and permitted claims |

---

## 1. Reading Rules

This matrix distinguishes four layers that must not be collapsed:

```text
adapter implemented
fixture semantics validated
live provider response observed
claim supported
```

An implemented adapter is not live evidence. A successful HTTP response is not automatically cache
evidence. A provider error is not a model or cache result.

---

## 2. Terminal Matrix

| Lineage | Adapter / boundary | Live execution | Observed evidence | Cache evidence level | Terminal state | Comparison eligibility |
|---|---|---|---|---|---|---|
| Fake provider | Deterministic test adapter | No external call | Fixed contract and failure fixtures | Fixture-only | Available for tests | Not live evidence |
| Ollama/local timing path | Local runtime adapter | Historical/local validation only | Prompt-evaluation timing where configured | Inferred local only | Supporting path | Cannot populate provider cached-token claims |
| Groq calibration and raw-wire reauthorization | Groq SDK plus raw HTTP capture | Two authorized successful raw-wire calls | `usage.prompt_tokens_details.cached_tokens` absent from both raw responses | Unavailable | Closed negative telemetry result | Ineligible |
| OpenRouter generic adapter | Typed OpenRouter completion plus generation reconciliation | Fixture-tested before live execution | Absent, null, zero, positive, invalid, and mismatch states | Fixture-only before live call | Adapter validated | Not sufficient alone |
| OpenRouter `tencent/hy3:free` capability probe | One-time recording transport and bounded runner | One cold attempt | HTTP `401`; `PROVIDER_AUTHENTICATION_FAILED`; zero successful completions | Unavailable before inference | Closed terminal provider failure | Ineligible |

---

## 3. Groq Lineage

### Evidence reached

```text
provider boundary reached: yes
successful model responses: 2
raw response capture: yes
required field checked at wire boundary: yes
required field state: absent in both responses
```

### Permitted claim

> For the two authorized Groq raw-wire calls, the required
> `usage.prompt_tokens_details.cached_tokens` field was absent from both successful raw responses.

### Blocked claims

```text
cache hit
cache miss
cached tokens equal zero
provider cache usage measured
provider cache savings measured
universal Groq omission behavior
```

### Why the lineage closed

The required measurement channel was not present in successful responses. Additional identical calls
would have lacked a new hypothesis and risked evidence fishing.

---

## 4. OpenRouter / Hy3 Lineage

### Evidence reached

```text
metadata-only key preflight: passed
model catalog preflight: passed
protected prompt bundle: prepared
one-time execution runner: merged before execution
cold call attempted: yes
HTTP response observed: 401
successful model response: no
generation metadata requested: no
warm call attempted: no
cache telemetry observed: no
```

### Permitted claim

> The one-time OpenRouter Hy3 capability probe closed on its first cold-call attempt after OpenRouter
> returned HTTP `401`; no successful completion, generation metadata, route identity, or cache
> telemetry was obtained.

### Blocked claims

```text
Hy3 model unavailable
privacy-compatible route unavailable
OpenRouter cache telemetry absent from a successful response
cache hit or miss
cache write or read
cache discount
route affinity
latency improvement
cost saving
```

### Root-cause boundary

The public evidence retains:

```text
provider message: Missing Authentication header
local post hoc Bearer-header construction: passed
system proxy detected: false
credential continuity proven: false
exact live header delivery proven: false
root cause resolved: false
```

The post hoc local test does not prove what OpenRouter received during the live call.

---

## 5. Cross-Provider Conclusion

The two terminal lineages failed at different evidence stages:

```text
Groq:
  inference succeeded
  required cache telemetry field absent

OpenRouter/Hy3:
  request reached provider
  authentication failed before successful inference
  cache telemetry boundary never reached
```

Therefore:

```text
provider cache usage measured: false
provider cache savings measured: false
A/B/C comparison eligible: false
pilot authorized: false
retained benchmark authorized: false
```

The valid project result is the fail-closed decision, not a positive or negative cache-performance
number.

---

## 6. Maturity Interpretation

`Controlled-provider tested` is permitted because AuraGateway exercised provider boundaries under
explicit call budgets, authorizations, evidence retention, and terminal closeout rules.

It does not mean:

```text
provider-specific cache benchmark validated
customer-data tested
deployed
production-ready
```

---

## 7. Future Provider-Lineage Requirements

A new provider experiment must be a new lineage, not a rerun. Before any live call it must define:

```text
new provider/model identity
new telemetry authority
new measurement sufficiency rule
new credential-continuity control
whitespace-rejection rule
non-sensitive exact-request header-construction evidence
new one-time authorization
new protected evidence namespace
new stop, retry, resume, and rerun policy
new claims and non-claims
```

No future lineage may mutate or reinterpret the Groq or OpenRouter/Hy3 terminal evidence.
