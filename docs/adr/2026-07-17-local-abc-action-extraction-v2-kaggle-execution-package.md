# ADR: Freeze the Action-Extraction Requalification Kaggle Package v2

**ADR ID:** `ADR-LOCAL-ABC-ACTION-EXTRACTION-KAGGLE-PACKAGE-V2`
**Date:** 2026-07-17
**Status:** Accepted execution-package candidate
**Source notebook merge:** `1cbb01e72fc624b71be1faef9da199a1556d2f0c`

## Context

PR #89 merged the statically qualified 16-case action-extraction requalification notebook. The
notebook is hash-bound, has no saved execution state, compiles all code cells, and remains attached
to one fresh unused authorization.

The next boundary is operational packaging. The package must be reproducible, inspectable, and
small enough to attach to Kaggle without introducing another source-of-truth copy or hidden runtime
behavior.

## Decision

Create one deterministic two-member ZIP containing only:

```text
benchmarks/local_abc/reconcile_balance_extraction_requalification_notebook_binding_v2.json
notebooks/kaggle/auragateway_v2_reconcile_balance_action_extraction_requalification_v2.ipynb
```

Use stored ZIP members with fixed timestamps, stable Unix permissions, and canonical member order.
The package SHA-256 is therefore reproducible across machines rather than depending on local ZIP
timestamps or compression-library behavior.

The repository stores a typed package contract and deterministic builder. The generated ZIP remains
an operator artifact and is not committed.

## Execution boundary

```text
merged PR #89 notebook qualification
    ↓
deterministic execution package
    ↓
operator verifies package PR merge and package SHA
    ↓
one complete Kaggle execution
    ↓
evidence archive download
    ↓
immutable evidence audit
```

The package PR performs no model request and consumes no authorization.

## Alternatives considered

### Commit the generated ZIP

Rejected. Binary archives add repository churn and duplicate source files already governed by Git.

### Use ordinary compressed ZIP output

Rejected. ZIP timestamps and compression implementation differences can change archive bytes even
when source files are identical.

### Add the package manifest inside the ZIP

Rejected. Embedding an archive digest in an archive member creates a circular identity problem. The
external typed manifest binds the exact two source members and the final deterministic archive.

### Run Kaggle as part of package construction

Rejected. Packaging and execution are separate state transitions with different evidence and
rollback requirements.

## Consequences

### Positive

- The exact upload package is reproducible from the merged repository.
- Package drift is detected before upload.
- The operator receives one clear artifact and one permitted execution attempt.
- The evidence audit can bind the exact package used for execution.

### Negative

- The operator must generate or download the package separately from the repository slice.
- The package-merge check remains an explicit operator control because the frozen notebook predates
  this packaging PR.

## Safety and privacy controls

```text
execution_attempt_limit=1
request_count=16
request_attempts_per_case=1
hidden_retries=0
repairs=0
replacement_requests=0
raw_prompt_retention=false
raw_output_retention=false
raw_action_retention=false
token_id_retention=false
customer_data_used=false
external_spend=0
cache_claims_permitted=false
full_measured_rerun_authorized=false
```

## Next gate

```text
immutable_action_extraction_v2_execution_evidence_audit
```
