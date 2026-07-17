# ADR: Integrate Hardened Scoring and Cleanup into the Full A/B/C Harness

**ADR ID:** `ADR-LOCAL-ABC-FULL-ABC-HARNESS-INTEGRATION-DESIGN`
**Date:** 2026-07-18
**Status:** Accepted
**Source merge:** `b995794e1e1f312c23f39a685b3c118253707700`

## Context

The action-extraction requalification passed 16/16 but exposed two harness defects: stale score prompt
identity and an overstated cleanup label. PR #93 corrected both locally by adding explicit executed-prompt
identity injection and evidence-derived three-state cleanup classification.

The full AuraGateway A/B/C benchmark constitution already freezes the experimental conditions, causal
contrasts, schedules, quality non-inferiority gate, privacy boundary, and claim precedence. What remained
undefined was how every condition would consume the hardened scoring and cleanup boundaries without
introducing a condition-specific confound.

The existing provider evidence lineages remain terminally closed. The execution manifest is not frozen,
and no measured A/B/C execution is authorized.

## Decision

Create a typed integration design that requires Conditions A, B, and C to share:

- the same v2 action-extraction scorer;
- the same executed-prompt identity propagation rule;
- the same three-state cleanup classifier;
- the same prompt policy, response schema, and deterministic action schema;
- the same retrieval configuration, output schema, and quality rubric.

Only the frozen causal dimensions may differ:

```text
Condition A: cache-hostile context, turn-local route
Condition B: deterministic context, turn-local route
Condition C: deterministic context, cache-affinity plus TTL route
```

The design also binds the functional and runtime schedules, telemetry claim gate, privacy exclusions,
and trace fields required to prove hardened score and cleanup lineage.

## Why this design is necessary

Without one shared scorer and cleanup classifier, an A/B/C result could be confounded by condition-specific
instrumentation rather than context or route policy. A fast condition must not receive weaker score
traceability or more permissive cleanup semantics.

The new trace fields make the two hardening results queryable:

```text
score_prompt_policy_sha256
score_rendered_prompt_sha256
cleanup_status
cleanup_warning_codes
```

## Alternatives rejected

### Implement the runner immediately

Rejected because the execution manifest, corpus, retrieval assets, held-out manifests, rubric exports,
and provider sufficiency decision are not frozen. A runner before those assets exist would create a
false sense of execution readiness.

### Use separate scorers for each condition

Rejected because scorer differences would become a quality confound and could recreate the stale prompt
identity defect.

### Treat cleanup as an operator note

Rejected because cleanup quality affects run validity and must be machine-readable before comparison
eligibility and claims are calculated.

### Reopen the consumed action-extraction authorization

Rejected because the authorization is consumed and this design requires no model execution.

## Consequences

### Positive

- A/B/C differences remain attributable to the frozen causal dimensions.
- Score metadata binds the prompt actually executed by every condition.
- Cleanup warnings cannot be hidden behind a closed port.
- Quality, telemetry, privacy, and comparison eligibility remain fail-closed.
- Implementation can proceed locally without a new authorization.

### Negative

- The future runner must expose the same integration interfaces for all conditions.
- More trace fields and validation gates are required.
- Execution remains blocked until downstream assets and a separate authorization review exist.

## Execution posture

```text
execution_manifest_frozen=false
measured_execution_authorized=false
gpu_execution_authorized=false
provider_execution_authorized=false
new_authorization_issued=false
consumed_authorization_reused=false
```

No model request, GPU execution, provider call, or credential access is performed by this design.

## Next gate

```text
full_abc_harness_integration_implementation
```
