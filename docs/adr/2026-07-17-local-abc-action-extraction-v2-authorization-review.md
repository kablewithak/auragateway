# ADR: Review Action-Extraction Remediation v2 Before Activation

**Status:** Accepted inactive review
**Date:** 2026-07-17
**Source merge:** `bb732bf88020cb031f534bb0b67d74b8f8f05483`
**Decision:** Approve a separate activation slice; do not authorize execution here

## Context

The v1 action-extraction canary completed all 12 authorized requests but failed the semantic
quality gate at 10/12 exact operands and final answers. PR #85 preserved that failed diagnostic
as immutable evidence. PR #86 introduced a versioned remediation candidate:

- deterministic integer lexical normalization;
- semantic role-bound extraction instructions;
- role-described response-schema fields;
- the original 12 cases plus four hard diagnostics.

The remediation is locally validated but unmeasured. The consumed v1 authorization cannot be
reused, and the full Local A/B/C benchmark remains blocked.

## Decision

Create an inactive authorization review that:

1. binds the exact PR #86 merge commit and merged source blobs;
2. binds the v2 remediation manifest, plan, normalization policy, prompt policy, response schema,
   and unchanged action schema;
3. freezes a complete 16-case, one-attempt schedule;
4. reuses the previously qualified model and runtime identities;
5. requires 16/16 exact operands and 16/16 exact final answers;
6. preserves zero retries, repairs, replacements, and semantic-parser fallback;
7. retains hash-only prompt lineage and normalization counts;
8. permits only a later, separate activation artifact.

The review is `review_ready_inactive`. It creates no active authorization, notebook, execution
command, credential access, model request, or GPU permission.

## Material difference

The proposed execution would be materially different from the failed v1 canary because it changes
three explicitly versioned controls:

```text
deterministic integer lexical normalization
semantic role-bound instruction
role-described response schema
```

The model, tokenizer, runtime, decoding, strict action contract, deterministic executor, privacy
boundary, and one-attempt policy remain fixed. This isolates the quality intervention rather than
confounding it with a model upgrade or retry policy.

## Alternatives rejected

### Reuse the consumed v1 authorization

Rejected. The prior authorization completed all 12 requests and is permanently consumed.

### Activate and execute in one PR

Rejected. It would collapse review, authorization, notebook generation, and execution into one
unreviewable boundary.

### Retry only the two historical failures

Rejected. It would create selection bias and conceal regressions across the other ten cases.

### Add a deterministic semantic parser

Rejected. It would replace the extraction task rather than test the versioned model-boundary
remediation.

### Upgrade the model

Rejected. It would confound the intervention and weaken the before/after causal interpretation.

## Consequences

### Positive

- The next authorization can be reviewed against exact immutable inputs.
- The 16-case schedule is inspectable before any GPU use.
- The intervention remains causally legible.
- Failed cases cannot be selectively retried.
- Raw prompts and outputs remain outside repository evidence.

### Negative

- One additional PR is required before notebook generation.
- Passing local tests still does not establish measured model improvement.
- The later activation must bind its own merge commit and a new notebook hash.

## Guardrails

```text
active_authorization_created=false
execution_command_available=false
notebook_generation_permitted=false
execution_authorized=false
gpu_execution_authorized=false
failed_case_only_execution_permitted=false
cache_measurement_in_scope=false
cache_claims_permitted=false
full_measured_rerun_authorized=false
external_spend=0
customer_data_used=false
```

## Next gate

```text
bounded_action_extraction_v2_authorization_activation
```

That later slice may create one fresh 16-request authorization. It must still perform no model or
GPU execution and must not authorize the full A/B/C benchmark.
