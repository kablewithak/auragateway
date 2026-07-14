# AuraGateway OpenRouter Hy3 Free-Tier Validation Mini PRD

| Field | Value |
|---|---|
| Document version | 1.0.0 |
| Status | Planned experimental extension |
| Project | AuraGateway v2 |
| Time budget | 40–50 hours; planned baseline 48 hours |
| Model under test | Tencent Hy3 |
| Initial serving environment | OpenRouter `tencent/hy3:free` |
| Gateway provider | OpenRouter |
| Telemetry authority | OpenRouter-normalized usage |
| Execution posture | Local-first, bounded, evidence-gated |
| Data posture | Synthetic public-safe inputs only |
| Relationship to closed Groq work | New provider lineage; Groq evidence remains immutable |
| Paid usage | Not required for completion |
| Publication target | Sanitized Hugging Face Dataset and static Space after terminal review |

---

## 1. Purpose

Determine whether AuraGateway can obtain trustworthy cache-use telemetry for Tencent Hy3 through
OpenRouter's free route and, only if the telemetry path is valid, run a bounded comparison of:

- unstable versus deterministic context construction; and
- deterministic context without retained affinity versus deterministic context with retained affinity.

The experiment must stop rather than manufacture a cache, cost, latency, or routing claim when the
required evidence is missing or ambiguous.

---

## 2. North Star

Answer two separate questions:

### 2.1 Context determinism

```text
Condition A:
unstable prefix
unique session identity per request

Condition B:
deterministic stable prefix
unique session identity per request
```

Question:

> Does deterministic context construction improve OpenRouter-reported cache reuse for the tested Hy3
> free route?

### 2.2 Affinity retention

```text
Condition B:
deterministic stable prefix
unique session identity per request

Condition C:
deterministic stable prefix
stable AuraGateway-derived session identity
```

Question:

> Does retained affinity improve OpenRouter-reported cache reuse for the tested Hy3 free route?

The experiment must not conflate these two hypotheses.

---

## 3. Experimental Boundary

### 3.1 Fixed boundary

```text
gateway_provider:
openrouter

requested_model:
tencent/hy3:free

model_family:
Tencent Hy3

telemetry_authority:
openrouter_normalized_usage

primary telemetry:
usage.prompt_tokens_details.cached_tokens
usage.prompt_tokens_details.cache_write_tokens
cache_discount, when available

secondary telemetry:
prompt_tokens
completion_tokens
resolved model
resolved upstream provider
generation ID
total latency
time to first token, when available
```

### 3.2 Provider and model distinction

AuraGateway will implement an `OpenRouterProviderAdapter`.

It will not implement a Hy3-specific core abstraction.

Hy3 is model configuration behind the OpenRouter adapter:

```text
model_alias:
openrouter-hy3-free

exact_model_identifier:
tencent/hy3:free
```

Future paid or self-hosted Hy3 routes must use separate configurations and separate evidence lineages.

### 3.3 Claim authority

Permitted telemetry wording:

> OpenRouter reported N cached input tokens for the recorded Hy3 request and resolved route.

Prohibited wording:

> Tencent directly reported N cached tokens.

The raw API boundary in this experiment is OpenRouter, not Tencent infrastructure.

---

## 4. Success Is Evidence Quality, Not a Positive Result

The sprint has three valid terminal outcomes:

```text
1. Cache telemetry unavailable
2. Numeric telemetry available, but cache use not observed
3. Numeric telemetry and cache use available; comparison eligible
```

A negative or unavailable result is acceptable when it is:

- captured through a fixed protocol;
- typed and hash-bound;
- non-retry-contaminated;
- represented without converting unknown into zero;
- accompanied by explicit claims and non-claims.

---

## 5. Core Requirements

### R1 — Generic adapter

Implement a provider-neutral OpenRouter adapter that preserves:

- requested and resolved model identity;
- resolved upstream provider identity when available;
- generation identity;
- normalized usage;
- cache-read and cache-write observation states;
- request, prefix, session, raw-response, and parsed-response hashes;
- metadata-safe error envelopes.

### R2 — Observation-state integrity

Every cache telemetry field must resolve to one of:

```text
field_absent
field_null
observed_zero
observed_positive
invalid_type
generation_details_mismatch
```

Absent and null must never be converted to zero.

### R3 — Experimental identifiability

The harness must explicitly isolate:

- context determinism in A versus B; and
- session affinity in B versus C.

OpenRouter's own implicit sticky routing must be treated as a confounder and controlled through explicit
session identities.

### R4 — Bounded execution

The live path must use:

- one-time authorizations;
- exact call ceilings;
- deterministic requests;
- write-through journals;
- retry limits restricted to transient pre-evidence failures;
- immutable terminal reports and manifests;
- no hidden or automatic reruns.

### R5 — Privacy

Use only synthetic public-safe prompts.

Do not send or publish:

- customer data;
- user messages;
- private repository documents;
- historical `.local` prompt bundles;
- credentials;
- raw provider bodies in public evidence;
- raw prompts in public evidence.

### R6 — Evidence-gated promotion

No pilot or retained benchmark may run until the capability probe proves:

- numeric cache telemetry is available; and
- at least one defensible cache-write or warm cache-read observation exists.

---

## 6. Architecture

```text
AuraGateway core
    -> provider-neutral request contract
        -> OpenRouterProviderAdapter
            -> OpenRouter
                -> requested model: tencent/hy3:free

OpenRouter response
    -> protected raw capture
    -> parsed adapter result
    -> normalized cache observation
    -> typed run record
    -> public metadata-only evidence
    -> terminal claim gate
```

### 6.1 Protected boundary

```text
.local/benchmark/openrouter-hy3-*/
```

Protected locally:

- raw OpenRouter response bodies;
- parsed full provider objects;
- synthetic prompt body where necessary;
- API-derived content not approved for public release.

Publicly allowed:

- hashes;
- byte counts;
- numeric usage;
- model and provider identifiers;
- timestamps and durations;
- observation states;
- bounded error codes;
- claim decisions.

---

## 7. Phased Plan

## Phase 0 — Experimental charter

**Budget: 2 hours**

Deliver:

- ADR;
- exact A/B/C definitions;
- telemetry authority statement;
- claim and non-claim matrix;
- provider/model/service distinction;
- call ceilings;
- stop conditions.

Gate:

```text
experimental boundary frozen
no unresolved ambiguity about A, B, or C
```

---

## Phase 1 — Non-live route and identifiability review

**Budget: 3 hours**

Verify:

- `tencent/hy3:free` remains available;
- session identity is accepted;
- resolved route can be recorded;
- privacy-compatible routing remains possible;
- OpenRouter cache fields and generation-details schema are usable;
- free quota is sufficient for the probe;
- unnecessary request parameters are excluded;
- endpoint count and route stability assumptions are documented.

Gate 1:

```text
exact route available
session identity accepted
resolved route observable
synthetic-data policy acceptable
free quota sufficient for probe
```

Failure result:

```text
openrouter_hy3_free_experiment_not_identifiable
```

---

## Phase 2 — Generic OpenRouter adapter

**Budget: 7 hours**

Implement typed request and response contracts.

### Required request fields

```text
model
messages
session_id
maximum_completion_tokens
temperature
streaming
provider privacy constraints
trace_id
run_id
```

### Required response fields

```text
requested_model
resolved_model
gateway_provider
resolved_upstream_provider
generation_id
prompt_tokens
completion_tokens
cached_tokens
cache_write_tokens
cache_discount
cache_observation_state
telemetry_authority
latency_ms
raw_response_sha256
parsed_response_sha256
```

Acceptance:

- absent, null, zero, positive, invalid, and mismatch fixtures pass;
- secrets and message bodies are not logged;
- adapter remains model-agnostic;
- fake client tests cover provider failures and malformed usage.

---

## Phase 3 — Capability-probe harness and authorization

**Budget: 4 hours**

Build:

- synthetic 12K–16K-token stable prefix;
- deterministic suffix generator;
- stable-prefix SHA-256;
- deterministic session ID derivation;
- fake OpenRouter client;
- one-time authorization;
- bounded runtime policy;
- write-through journal;
- run records;
- terminal report;
- manifest;
- validator and closeout path.

### Probe call policy

```text
maximum successful calls:
2

maximum total inference attempts:
4

replacement attempt permitted:
only for a pre-evidence 429 or upstream-capacity failure

successful response with absent, null, zero, or positive telemetry:
no retry

authentication, validation, privacy, or contract failure:
stop immediately
```

---

## Phase 4 — Live telemetry capability probe

**Budget: 2 hours**

Run one controlled cold/warm pair:

```text
Call 1:
large stable prefix
stable session identity
suffix A

Call 2:
same exact stable prefix
same stable session identity
suffix B
```

Capture:

- raw and parsed response hashes;
- generation IDs;
- requested and resolved model;
- resolved provider;
- prompt tokens;
- cached tokens;
- cache-write tokens;
- cache discount;
- prefix and session hashes;
- duration;
- terminal observation state.

No pilot is permitted before this probe closes.

---

## Phase 5 — Capability decision

**Budget: 2 hours**

This is the main decision point at approximately hour 20.

### Outcome A — Telemetry unavailable

```text
cached_tokens absent or null
cache_write_tokens absent or null
generation details provide no numeric evidence
```

Decision:

```text
close capability path
do not run A/B/C
```

### Outcome B — Numeric schema available, no cache use observed

```text
cached_tokens = 0
cache_write_tokens = 0
```

Numeric zero proves schema availability, not cache use.

Permit at most one redesigned confirmation pair only when a specific, documented cacheability defect is
identified.

### Outcome C — Cache use observed

```text
cache_write_tokens > 0
or
warm cached_tokens > 0
```

Decision:

```text
promote to A/B/C pilot eligibility
```

### Outcome D — Route instability

```text
resolved model changes
resolved provider cannot be identified
or route changes invalidate attribution
```

Decision:

```text
cache telemetry may be retained
Condition C claim remains blocked
```

---

## Phase 6 — Small A/B/C pilot

**Budget: 6 hours**

Run one cold/warm pair per condition:

```text
A: 2 successful calls
B: 2 successful calls
C: 2 successful calls
```

Purpose:

- validate execution mechanics;
- confirm numeric telemetry across all conditions;
- verify prefix hashes;
- verify request-parameter parity;
- confirm route visibility;
- confirm quality-equivalent synthetic tasks;
- identify contamination before the retained benchmark.

Gate 3:

```text
all conditions yield valid numeric telemetry
prefix identities reconcile
request parameters reconcile
route identity is captured
quality acceptance is equivalent
no hidden retry contamination
```

---

## Phase 7 — Retained benchmark

**Budget: 8 hours**

Target:

```text
4 valid cold/warm pairs per condition
24 successful calls
```

Minimum acceptable:

```text
3 valid cold/warm pairs per condition
18 successful calls
```

### Primary metrics

- cached tokens;
- cache-write tokens;
- cached-token ratio;
- uncached input tokens;
- cache discount;
- cache-positive pair count;
- valid and invalid pair counts.

### Secondary metrics

- total latency;
- time to first token, when available;
- completion tokens;
- route stability.

Latency must not be treated as proof of caching.

### Pair validity

A retained pair requires:

```text
same requested model
same resolved model
same resolved provider, where provider identity is available
same stable-prefix hash for B and C
fixed request parameters
valid numeric telemetry
no unauthorized retry
```

Invalid pairs remain in the evidence archive with explicit failure labels.

---

## Phase 8 — Evaluation and report

**Budget: 5 hours**

Produce:

- fixed-case dataset;
- baseline and intervention definitions;
- pair-level result table;
- invalidated-pair table;
- failure taxonomy;
- cache telemetry distributions;
- cache-positive rate;
- medians;
- before/after report;
- claim and non-claim matrix;
- trace review;
- regression gate;
- small-sample limitations.

No improvement claim is permitted from one positive hit or one favorable latency observation.

Condition C requires a repeatable directional advantage across multiple valid pairs.

---

## Phase 9 — Terminal review and continuity update

**Budget: 4 hours**

Update:

- project-level terminal evidence review;
- PRD;
- session brief;
- handover;
- README;
- provider-adapter matrix;
- maturity labels;
- claims and non-claims.

Possible terminal states:

```text
openrouter_hy3_free_comparison_completed
openrouter_hy3_free_telemetry_available_benchmark_inconclusive
openrouter_hy3_free_cache_telemetry_unavailable
openrouter_hy3_free_condition_c_not_identifiable
```

The closed Groq lineage must remain immutable and independently valid.

---

## Phase 10 — Hugging Face publication integration

**Budget: 5 hours**

Publish sanitized, precomputed evidence for:

- Groq negative telemetry result;
- Hy3 capability result;
- A/B/C result, only when eligible;
- provider landscape;
- claim matrix;
- gate decisions;
- pair-level sanitized summaries;
- evidence hashes;
- methodology;
- limitations.

No API key, live inference, raw prompt, customer data, or raw provider body may enter the publication
layer.

---

## 8. Time Allocation

| Phase | Hours |
|---|---:|
| Experimental charter | 2 |
| Route and identifiability review | 3 |
| Generic OpenRouter adapter | 7 |
| Probe harness and authorization | 4 |
| Live capability probe | 2 |
| Capability decision | 2 |
| A/B/C pilot | 6 |
| Retained benchmark | 8 |
| Evaluation and report | 5 |
| Terminal review | 4 |
| Hugging Face integration | 5 |
| **Total** | **48** |

Only the first 20 hours are initially authorized.

The remaining 28 hours are activated only when the capability gate passes.

---

## 9. Call Budget

```text
Capability probe:
2 successful calls
maximum 4 attempts

Pilot:
6 successful calls

Retained benchmark:
18–24 successful calls

Expected successful total:
26–32 calls

Absolute inference ceiling:
40 attempts
```

The ceiling includes explicitly authorized transient-capacity replacement attempts.

The harness must stop before the ceiling and must not silently extend it.

---

## 10. Claim Matrix

### Permitted before live execution

- an OpenRouter adapter and typed telemetry boundary were implemented;
- A/B/C conditions were frozen;
- synthetic fixtures validate cache observation states;
- execution limits and privacy controls are enforced.

### Permitted after numeric telemetry is observed

- OpenRouter returned numeric cached-token or cache-write values;
- numeric zero is an observed zero, not an absent value;
- the requested and resolved route identities recorded in evidence are accurate.

### Permitted after cache use is observed

- OpenRouter reported cache writes or cache reads for the exact tested requests;
- the tested Hy3 free route produced the recorded cache-use observation.

### Permitted after an eligible benchmark

- bounded A versus B results under the exact tested OpenRouter Hy3 free conditions;
- bounded B versus C results under the exact tested OpenRouter Hy3 free conditions;
- directional differences supported by multiple valid pairs.

### Always blocked unless separately proven

- Tencent directly reported the normalized telemetry;
- Hy3 inherently provides a particular cache benefit;
- free-route results generalize to paid Hy3;
- free-route results generalize to self-hosted Hy3;
- cache misses occurred when fields were absent;
- cached tokens were zero when fields were absent or null;
- latency differences prove caching;
- universal cost or latency savings;
- production readiness.

---

## 11. Stop Conditions

Stop live execution and close the path when:

- cache fields remain absent or null after the bounded capability probe;
- privacy-compatible routing is unavailable;
- route identity cannot be captured sufficiently for the intended claim;
- the free route becomes unavailable;
- authentication or contract validation fails;
- the absolute call ceiling is reached;
- repeated transient capacity failures prevent the minimum valid cases;
- a required evidence file cannot be written or verified;
- historical evidence would need to be mutated;
- the only remaining path requires evidence fishing.

---

## 12. Validation Gates

Every meaningful slice must pass:

```text
focused pytest cases
full pytest suite
ruff check
ruff format --check
strict mypy
git diff --check
typed artifact validation
source and output hash reconciliation
no tracked .local files
no secrets or prompt bodies in logs
```

Live execution requires an explicit one-time confirmation phrase and terminal receipt review before
staging evidence.

---

## 13. Maturity and Non-Claims

This extension may become:

```text
Production-shaped
Locally validated
Synthetic-data validated
Controlled-provider tested
Provider-specific benchmark validated, only if all gates pass
```

It will remain:

```text
Not customer-data tested
Not deployed
Not production-ready
```

The free route's time-limited availability must be stated in the terminal report and publication layer.

---

## 14. Commercial Translation

This extension strengthens the following consultancy offers:

### AI System Evaluation Audit

Proves whether provider telemetry can support cache, cost, and routing claims before a team relies on
them.

### Agent Harness Hardening Sprint

Adds typed provider adapters, bounded execution, route identity, telemetry states, and fail-closed
claims.

### AI Reliability Pilot

Runs a small, controlled provider experiment before authorizing a larger benchmark or architecture
change.

### AI Reliability Retainer

Continuously protects teams from provider drift, missing metrics, accidental reruns, and unsupported
performance claims.

The buyer value is not a guaranteed positive cache result.

It is a trustworthy answer about whether the result can be measured and claimed.

---

## 15. Acceptance Criteria

The mini-project is complete when one terminal outcome is reached and frozen.

### Capability-only completion

```text
adapter validated
bounded live probe completed
telemetry availability classified
authorization consumed
terminal closeout produced
claims and non-claims frozen
```

### Full benchmark completion

```text
capability gate passed
pilot gate passed
minimum valid A, B, and C pairs retained
pair-level evidence preserved
invalid pairs labelled
A versus B and B versus C evaluated separately
claim matrix reconciled
terminal review completed
sanitized publication artifacts generated
```

### Final principle

```text
Do not spend the remaining benchmark hours until Hy3 proves that the measurement channel is usable.
```
