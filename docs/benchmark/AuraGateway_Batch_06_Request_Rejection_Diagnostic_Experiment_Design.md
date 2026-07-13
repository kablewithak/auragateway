# AuraGateway Batch 06 Request-Rejection Diagnostic Experiment Design

**Design ID:** `batch-06-request-rejection-diagnostic-design-v1`  
**Status:** `design_only`  
**Provider calls permitted:** No  
**Execution authorization included:** No  
**Next gate:** `fixture_materialization_review`

---

## 1. Purpose

Batch 06 produced one verified non-retryable HTTP 400 request rejection:

- failed run: `run-functional-ep-func-001-r03-condition-c`
- failed turn: `3`
- diagnostic family: `request_rejected`
- matched success: condition B turn 3
- matched system prompt hash: identical
- matched user prompt hash: identical
- matched prompt bytes: `8109`

The same provider-visible prompt later succeeded under condition B. The current evidence therefore points away from a deterministic prompt defect and toward a transient or hidden provider-state-dependent failure class.

This design freezes the next diagnostic questions before any new provider authorization.

---

## 2. Competing hypotheses

### H1 — Deterministic request defect

The same request shape is invalid across labels, sequence positions, cohorts, and spacing.

### H2 — First-sequence state effect

The first sequence using a previously unseen stable prefix fails regardless of whether condition B or C executes first.

### H3 — Spacing-sensitive state

Rapid zero-second repeated-prefix calls fail while matched thirty-second cells complete.

### H4 — Hidden condition-specific harness difference

Condition C fails across order and spacing while provider-visible equivalent condition B succeeds.

### H5 — Transient provider/backend event

Failures remain isolated or inconsistent and do not align with request shape, order, spacing, or condition label.

These are diagnostic hypotheses, not claims.

---

## 3. Frozen experiment matrix

The design contains eight three-request sequences and a hard maximum of 24 provider calls.

### Stage A — Order reversal

Two matched stable-prefix cohorts reverse which local label executes first:

| Cohort | First sequence | Second sequence | Inter-turn delay |
|---|---|---|---:|
| alpha | B | C | 0 seconds |
| beta | C | B | 0 seconds |

A minimum 300-second gap separates sequences.

This checks whether failure follows first position or condition label.

### Stage B — Spacing matrix

Four independent stable-prefix cohorts cover the full label-by-spacing matrix:

| Cohort | Label | Inter-turn delay |
|---|---|---:|
| gamma | B | 0 seconds |
| delta | B | 30 seconds |
| epsilon | C | 0 seconds |
| zeta | C | 30 seconds |

Each spacing cohort executes one isolated three-request sequence.

---

## 4. Prompt cohort materialization boundary

The six cohorts are intentionally `pending`.

A later non-live fixture slice must prove:

- three turns per cohort;
- exact source byte counts: `7365`, `7737`, `8109`;
- input-token estimates within 25 tokens of `1732`, `1809`, `1884`;
- a unique stable prefix for every cohort;
- byte-identical provider-visible requests for B and C inside a matched cohort;
- synthetic content only;
- no PII or secrets;
- no raw prompt committed to Git.

No authorization may be created while any cohort remains pending.

---

## 5. Stop and continuation rules

A safely retained `PROVIDER_REQUEST_REJECTED` observation:

- stops the current sequence;
- receives no retry;
- permits the next predeclared sequence to continue.

The entire experiment stops on:

- ambiguous provider response;
- authentication, permission, model, SDK, or configuration failure;
- protected diagnostic retention failure;
- request-shape mismatch;
- unplanned sequence;
- attempt or cost budget exhaustion;
- raw sensitive-data boundary violation.

Resume is forbidden. An interrupted experiment requires a new reviewed authorization.

---

## 6. Required trace fields

The later execution harness must retain only metadata-safe evidence:

- design, sequence, stage, cohort, condition, and order identities;
- turn index;
- planned and observed spacing;
- system and user prompt hashes;
- prompt byte count;
- input-token estimate;
- provider status and bounded error code;
- allowlisted rejection reason;
- provider request-ID hash;
- adapter version;
- estimated cost;
- protected diagnostic retention status.

It must not retain raw prompts, raw request messages, credentials, headers, provider error messages, or raw provider outputs in public evidence.

---

## 7. Interpretation rules

The matrix can strengthen or weaken hypotheses. It cannot establish provider internals from one small diagnostic execution.

Examples:

- first sequence fails in alpha and beta, regardless of label: H2 strengthened;
- zero-second cells fail and thirty-second cells succeed for both labels: H3 strengthened;
- C fails across order and spacing while B succeeds: H4 strengthened;
- the same turn fails everywhere: H1 strengthened;
- no stable pattern: H5 strengthened.

No cost, latency, quality, cache-savings, benchmark, or production-readiness claim is permitted.

---

## 8. Acceptance for this design slice

This design slice passes when:

- typed plan validation passes;
- plan and manifest hashes reconcile;
- Batch 06 public evidence identities reconcile;
- Batch 06 outcome remains 3 terminal records, 11 attempts, 2 completed runs, and 1 provider error;
- no authorization file exists;
- provider calls remain disabled;
- all six cohorts remain pending;
- the eight-sequence matrix contains exactly 24 maximum calls;
- tests, Ruff, formatting, mypy, and diff checks pass.

The next slice is prompt-cohort materialization and equivalence proof. It remains non-live.
