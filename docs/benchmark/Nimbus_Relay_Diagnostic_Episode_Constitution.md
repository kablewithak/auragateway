# Nimbus Relay Diagnostic Episode Constitution

Version: **1.0.0**
Status: **Frozen**
Gate: **Gate 2 — Diagnostic Eval Readiness**

## Purpose

This constitution defines the frozen multi-turn diagnostic workload used to evaluate AuraGateway task quality, evidence use, terminal decisions, feedback retention, and later runtime behaviour. It is bound to the Gate 1 retrieval configuration fingerprint:

```text
220ce9ac6e19789bedf1aedc2b6253db5ba03a09ebcc6efdac203eb80cd23490
```

No accepted episode, split assignment, expected terminal decision, source scope, failure hypothesis, failure label, or runtime-subset membership may change without versioning the episode assets and invalidating affected downstream comparisons.

## Asset Shape

```text
Functional episodes: 18
Development: 12
Held out: 6
Turns per episode: 4
Runtime microbenchmark subset: 6
Rejected proposals retained: 8
```

Each accepted episode contains:

- a concrete failure hypothesis;
- one primary diagnostic family;
- four ordered synthetic user turns;
- required information gain per turn;
- expected per-turn decision;
- required, forbidden, and optional source IDs;
- one typed terminal-decision expectation;
- acceptable answer variants;
- machine-readable failure labels;
- an acceptance reason;
- a difficulty reason;
- an explicit functional split;
- runtime eligibility.

## Acceptance Standard

An episode is accepted only when it exposes a specific, grounded failure that can change the final action. Accepted episodes must not be trivial, ambiguous, duplicated, ungrounded, or dependent on customer data.

The frozen set covers every required diagnostic family:

```text
version_conflicting_sources
similar_error_codes
missing_required_parameters
incomplete_documentation
repeated_user_information
contradictory_user_correction
duplicate_retrieval_evidence
noisy_context_dilution
unsupported_requested_behaviour
model_capability_edge_cases
multi_turn_evidence_correction
provider_failure_mid_session
```

Additional coverage includes multi-source grounding and SDK-variant correction.

## Rejection Standard

Rejected proposals remain stored with a typed reason:

```text
trivial
ambiguous
duplicate
ungrounded
non_diagnostic
privacy_risk
```

Rejecting a proposal is evidence that the eval set was curated for diagnostic value rather than padded with easy cases.

## Terminal Decision Contract

Every episode ends in exactly one of:

```text
answer
clarify
escalate
refuse
```

### Answer

An answer requires:

- sufficient evidence;
- required claims;
- no forbidden claims;
- at least one required citation source;
- no stale or forbidden source use.

### Clarify

A clarification requires:

- explicit missing fields;
- a question capable of resolving the state;
- no unsupported assumptions;
- no premature answer.

### Escalate

An escalation requires:

- a typed escalation reason;
- evidence showing why local resolution is unsafe or impossible;
- no fabricated contact, service level, limit, or procedure.

### Refuse

A refusal requires:

- a typed capability, security, or grounding reason;
- no hidden substitution with unsupported advice;
- a safe alternative where one exists.

The runtime output schema is a discriminated Pydantic union. Fields from one terminal decision cannot leak into another decision type.

## Failure Taxonomy

The frozen failure taxonomy includes:

```text
STALE_SOURCE_SELECTED
FORBIDDEN_SOURCE_USED
MISSING_REQUIRED_SOURCE
UNSUPPORTED_CLAIM
INVALID_TERMINAL_DECISION
MISSING_CLARIFICATION
UNNECESSARY_CLARIFICATION
ESCALATION_BYPASSED
REFUSAL_BYPASSED
DUPLICATE_RETRIEVAL_EVIDENCE
REDUNDANT_FEEDBACK
UNRETAINED_FEEDBACK
CONTRADICTORY_STATE
NOISY_CONTEXT_DILUTION
CAPABILITY_MISMATCH
PROVIDER_FAILURE_UNHANDLED
BLIND_RETRY
INVALID_CITATION_ID
CITATION_UNSUPPORTED
STRUCTURED_OUTPUT_INVALID
PRIVACY_VIOLATION
TASK_INSUFFICIENT
```

These labels describe detectable harness failures. They are not model personality judgments.

## Frozen Functional Inventory

| Episode | Title | Family | Split | Terminal | Runtime eligible |
|---|---|---|---|---|---|
| `ep-func-001` | Current API key lifetime versus superseded guidance | `version_conflicting_sources` | `development` | `answer` | yes |
| `ep-func-002` | OAuth invalid grant without grant-type evidence | `missing_required_parameters` | `development` | `clarify` | yes |
| `ep-func-003` | Raw HTTP cursor pagination despite repeated SDK cues | `repeated_user_information` | `development` | `answer` | yes |
| `ep-func-004` | Distinguish conflict error 409 from validation error 422 | `similar_error_codes` | `development` | `answer` | no |
| `ep-func-005` | Multipart upload limit absent from incomplete guidance | `incomplete_documentation` | `development` | `escalate` | yes |
| `ep-func-006` | Unsupported production event simulation in sandbox | `unsupported_requested_behaviour` | `development` | `refuse` | yes |
| `ep-func-007` | Current webhook retry window versus legacy schedule | `version_conflicting_sources` | `development` | `answer` | no |
| `ep-func-008` | Webhook signature diagnosis missing timestamp and algorithm | `missing_required_parameters` | `development` | `clarify` | no |
| `ep-func-009` | Incident escalation guide lacks contacts and service levels | `incomplete_documentation` | `development` | `escalate` | no |
| `ep-func-010` | Resolve a custom-role 403 using two required sources | `multi_source_grounding` | `development` | `answer` | yes |
| `ep-func-011` | Current idempotency retention versus legacy retention | `version_conflicting_sources` | `development` | `answer` | no |
| `ep-func-012` | Retry policy retained despite noisy unrelated context | `noisy_context_dilution` | `development` | `answer` | yes |
| `ep-func-013` | Duplicate event-catalogue retrieval must not create extra confidence | `duplicate_retrieval_evidence` | `held_out` | `answer` | no |
| `ep-func-014` | Refuse recovery of a secret from redacted logs | `model_capability_edge_cases` | `held_out` | `refuse` | no |
| `ep-func-015` | Provider failure mid-session without blind duplicate generation | `provider_failure_mid_session` | `held_out` | `escalate` | no |
| `ep-func-016` | Correct an endpoint migration diagnosis after version evidence changes | `multi_turn_evidence_correction` | `held_out` | `answer` | no |
| `ep-func-017` | Contradictory account-plan corrections leave rate limit unresolved | `contradictory_user_correction` | `held_out` | `clarify` | no |
| `ep-func-018` | JavaScript SDK setup after an initial Python assumption | `sdk_variant` | `held_out` | `answer` | no |

## Runtime Microbenchmark Selection

The six runtime episodes are a frozen subset of the functional set:

```text
ep-func-001  answer
ep-func-002  clarify
ep-func-005  escalate
ep-func-006  refuse
ep-func-010  answer
ep-func-012  answer
```

The subset represents all four terminal decisions, stable context growth, multi-source retrieval, version conflict, missing state, incomplete documentation, unsupported behaviour, and noisy context. It excludes the injected provider-failure episode because provider-failure timing is evaluated through separate fault fixtures.

## Split Protection

Development and held-out episodes use separate episode IDs and may not reuse exact user messages. Held-out episodes may not be edited after results are inspected. A changed held-out episode requires a new episode-set version and invalidates affected downstream results.

## Blinded Review Protocol

The prepared protocol requires:

- primary review of 100% of functional trajectories;
- independent double review of 25%, rounded to five episodes;
- sampling seed `20260712`;
- independent adjudication for material disagreement;
- reviewers blinded to condition, provider, model, route, cost, latency, cache telemetry, and run order;
- protected review exports;
- no raw review content in public traces.

## Privacy Boundary

Raw user messages are synthetic benchmark inputs. They may exist inside version-controlled episode assets and protected review exports. Public traces and evidence summaries may retain only safe metadata such as episode ID, turn index, decision, failure labels, validation result, source IDs, and fingerprints.

Public traces must not contain:

- raw user messages;
- raw prompts;
- raw retrieved documents;
- raw model output;
- provider payloads;
- secrets;
- personal data.

## Invalidation Triggers

The episode freeze is invalidated by changes to:

- accepted episode content;
- rejected proposal evidence;
- split assignments;
- runtime selection;
- source scopes;
- terminal expectations;
- failure labels;
- review protocol;
- retrieval configuration fingerprint;
- typed episode or terminal-decision semantics.

## Evidence Boundary

This constitution proves that the diagnostic workload is typed, curated, split-protected, reviewable, and hash-bound. It does not prove model task quality, citation support, feedback retention, prefix determinism, provider readiness, cache effectiveness, or production readiness.
