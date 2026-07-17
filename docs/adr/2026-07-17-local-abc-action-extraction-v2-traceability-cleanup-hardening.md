# ADR: Harden Action-Extraction v2 Traceability and Cleanup Semantics

**ADR ID:** `ADR-LOCAL-ABC-ACTION-EXTRACTION-V2-TRACEABILITY-CLEANUP-HARDENING`
**Date:** 2026-07-17
**Status:** Accepted
**Source merge:** `fe25c0869f62624247cc12bb97c5185586845f22`

## Context

The governed action-extraction requalification passed all 16 cases but exposed two harness defects:

1. `evaluate_reconcile_balance_extraction` rebuilt a v1 prompt identity internally even when the caller
   executed a v2 normalized prompt and schema.
2. worker cleanup was classified as `CLEAN` from port closure alone, allowing forced termination and
   leaked-resource warnings to be hidden behind a successful terminal label.

The one-shot authorization is consumed. No model or GPU execution is required to correct either defect.

## Decision

Add an explicit executed-prompt identity seam to the base evaluator while preserving legacy default
behavior. Add a v2 scoring entry point that injects the identity produced by the remediation renderer.

Add an evidence-derived cleanup classifier with three states:

```text
CLEAN
CLEAN_WITH_RUNTIME_WARNINGS
FAILED
```

`CLEAN` requires return code zero, closed port, completed application shutdown, no forced termination,
and no leaked or surviving runtime resources.

## Alternatives rejected

### Rewrite all score contracts as v2

Rejected because the existing score schema already carries the policy, source-prompt, and rendered-prompt
hashes needed for correct attribution. A schema rewrite would add migration cost without correcting more
behavior.

### Infer prompt identity from case data inside the evaluator

Rejected because this caused the original defect. The evaluator cannot know which versioned renderer the
caller executed unless that identity crosses the boundary explicitly.

### Treat every runtime warning as an infrastructure failure

Rejected because warnings such as a leaked semaphore can coexist with a complete ledger, zero return code,
and closed port. They must block a perfect-cleanliness claim without erasing completed quality evidence.

### Modify the executed v2 notebook

Rejected because the notebook is frozen evidence under a consumed authorization. Future harnesses use the
new local entry points; historical evidence remains immutable.

## Consequences

### Positive

- Score metadata can bind the actual executed prompt version.
- Legacy callers retain their existing v1 behavior.
- Cleanup labels become evidence-derived and fail closed.
- Warning-qualified shutdowns remain distinguishable from both perfect cleanup and infrastructure failure.
- No authorization or model execution is required.

### Negative

- Future notebooks and A/B/C runners must call the v2 scoring wrapper explicitly.
- Cleanup observations must capture application-shutdown, escalation, and resource-leak facts.
- Existing historical score objects remain warning-qualified evidence rather than being rewritten in place.

## Next gate

```text
full_abc_harness_integration_design
```
