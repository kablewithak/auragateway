# ADR: Activate One Fresh Action-Extraction Requalification Authorization v2

**ADR ID:** `ADR-LOCAL-ABC-ACTION-EXTRACTION-AUTHORIZATION-ACTIVATION-V2`
**Date:** 2026-07-17
**Status:** Accepted activation candidate
**Source review merge:** `6038f7055e34c6c559b3c41cb919d0cb421b3e55`

## Context

The v1 action-extraction canary completed all 12 authorized requests but failed its semantic
quality gate at 10/12 exact operands and 10/12 exact answers. The evidence was audited and the
one-shot v1 authorization was consumed.

Remediation v2 introduced three versioned controls:

```text
deterministic_integer_lexical_normalization
semantic_role_bound_instruction
role_described_response_schema
```

PR #87 approved those controls for a separate authorization activation and froze a metadata-only
16-case schedule. The review intentionally created no active authorization and no execution path.

## Decision

Create one fresh, unused authorization for the complete 16-case requalification suite.

The authorization:

- binds the exact PR #87 merge and four source blobs;
- preserves the reviewed model, tokenizer, runtime, decoding, stop, evidence, privacy, and spend
  controls;
- permits notebook generation only after this activation merges;
- requires a separately hash-bound qualified notebook before any GPU enablement or model request;
- permits one attempt for each of the 16 cases;
- requires 16/16 exact operands and 16/16 exact final answers;
- prohibits failed-case-only execution, retries, repairs, replacements, cache claims, and the full
  measured A/B/C rerun;
- exposes no execution command in this slice.

## Execution boundary

```text
merged inactive review
    ↓
fresh active-unused authorization
    ↓
qualified notebook generation and binding
    ↓
separately governed one-shot execution
```

The activation is an authorization artifact, not an execution event.

## Alternatives considered

### Reuse the consumed v1 authorization

Rejected. It would violate one-attempt lineage and bind the wrong prompt, schema, and case set.

### Generate and execute the notebook in the activation PR

Rejected. It would collapse review, activation, notebook qualification, and execution into one
change, weakening rollback and evidence attribution.

### Authorize only the two historical failures

Rejected. It would inflate the result and omit regression evidence across the other 14 cases.

### Authorize the full A/B/C benchmark immediately

Rejected. The remediation has not yet passed the 16-case quality requalification gate.

## Consequences

### Positive

- One fresh authorization has an explicit unused state.
- Every later notebook must bind this authorization and its merge commit.
- The complete diagnostic constitution remains fixed.
- Execution and quality claims remain separated from authorization claims.

### Negative

- Another PR is required for notebook generation and qualification.
- GPU execution remains blocked until notebook identity is frozen.

## Safety and privacy controls

```text
external_spend=0
customer_data_used=false
raw_prompt_retention=false
raw_output_retention=false
raw_action_retention=false
token_id_retention=false
hidden_retries=0
repairs=0
replacement_requests=0
cache_claims_permitted=false
full_measured_rerun_authorized=false
```

## Next gate

```text
qualified_action_extraction_v2_notebook_generation
```
