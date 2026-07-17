# ADR: Qualify the Action-Extraction Requalification Notebook v2

**ADR ID:** `ADR-LOCAL-ABC-ACTION-EXTRACTION-NOTEBOOK-QUALIFICATION-V2`  
**Date:** 2026-07-17  
**Status:** Accepted notebook candidate  
**Activation merge:** `639e21a63eb8a37d0221c2630b756203d1270f62`

## Context

PR #88 created one fresh, unused authorization for the complete 16-case action-extraction
requalification suite. The authorization requires an exact notebook SHA-256 binding before any
GPU enablement or model request.

## Decision

Generate one frozen Kaggle notebook and bind its exact bytes, code-source digest, activation
lineage, 16-case order, runtime policy, model identity, one-attempt policy, privacy boundary, and
evidence filenames.

The notebook performs no execution in this PR. Static qualification requires:

- exactly 12 code cells;
- no stored execution counts or outputs;
- successful Python compilation of every code cell;
- exact PR #88 activation source and artifact bindings;
- the v2 normalization, role-bound prompt, and role-described response schema;
- exactly 16 one-attempt requests;
- no hidden retries, repairs, replacements, cache measurement, or full benchmark path;
- hash-only retained prompt and output evidence.

## Execution boundary

```text
fresh unused authorization
    ↓
frozen notebook plus exact binding
    ↓
post-merge Kaggle execution package
    ↓
one governed 16-request execution
```

## Alternatives rejected

### Execute while generating the notebook

Rejected. It would collapse artifact qualification and experimental execution.

### Reuse the v1 notebook unchanged

Rejected. It binds the consumed v1 authorization, old 12-case manifest, v1 prompt, and v1
response schema.

### Run only the two failed historical cases

Rejected. The authorization requires the complete 16-case regression constitution.

## Consequences

- The notebook can be inspected, hashed, compiled, and regression-tested locally.
- A later packaging step can attach the exact notebook and binding to Kaggle.
- No quality improvement claim exists until the notebook executes and evidence is audited.

## Next gate

```text
bounded_action_extraction_v2_kaggle_execution_package
```
