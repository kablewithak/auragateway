# ADR: Certify Action-Extraction Requalification v2 with Audit Warnings

**ADR ID:** `ADR-LOCAL-ABC-ACTION-EXTRACTION-V2-EVIDENCE-AUDIT`
**Date:** 2026-07-17
**Status:** Accepted
**Package merge:** `52dcd0564b26b917684faedaa46d2d038a9e0be7`

## Context

The governed v2 requalification completed all 16 authorized synthetic requests. Every request passed
JSON validation, action-schema validation, identity checks, exact operand comparison, deterministic
execution, and exact final-answer comparison. The one-shot authorization is consumed.

The retained evidence also exposes two harness-quality findings:

1. Every nested score object reused the legacy prompt-policy and rendered-prompt metadata even though
   the frozen schedule and outer ledger prove the v2 prompt and request identities.
2. The terminal report declared cleanup `CLEAN`, while the worker log recorded forced termination of
   one remaining process and one leaked semaphore.

## Decision

Certify the quality gate as passed while classifying the evidence as:

```text
CERTIFIED_PASSED_WITH_TRACEABILITY_AND_RUNTIME_WARNINGS
```

Do not rerun the experiment. Preserve the authorization as consumed. Require a local-only hardening
slice before full A/B/C authorization review.

## Rationale

The prompt-metadata defect is in score attribution, not the request schedule or outer ledger. The
actual v2 normalized prompt, rendered prompt, request body, and response evidence remain bound for
all 16 cases. The cleanup warnings do not erase the successful return code, closed port, completed
application shutdown, or complete ledger.

Reclassifying the run as failed would discard valid quality evidence. Calling the run perfectly clean
would conceal maintainability debt. The warning-qualified pass preserves both truths.

## Consequences

### Positive

- The 16/16 quality result is preserved without overstating evidence cleanliness.
- The consumed authorization cannot be reused.
- The next change is local harness hardening rather than another GPU experiment.
- Full A/B/C work remains blocked until traceability and cleanup semantics are corrected.

### Negative

- Score-level prompt identity cannot be treated as authoritative for this run.
- Cleanup must be described as successful with warnings, not perfectly graceful.
- Another repository slice is required before full benchmark authorization review.

## Next gate

```text
action_extraction_v2_traceability_cleanup_hardening
```
