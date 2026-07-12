# Nimbus Relay Retrieval Metadata Remediation Report

## Decision

```text
Development remediation: complete
Held-out v1 modified: no
Remaining development citation failures: 0
Gate 1: blocked pending held-out v2
Retrieval freeze permitted: no
```

## Before and after

### BM25 fixed-window

| Metric | Development v1 | Remediated development v2 |
|---|---:|---:|
| Recall@k | 1.000000 | 1.000000 |
| MRR | 0.972222 | 1.000000 |
| nDCG@k | 0.956280 | 0.977113 |
| Citation readiness | 0.916667 | 1.000000 |
| Unsupported retrieval | 0.098611 | 0.029167 |
| Metadata violations | 0.000000 | 0.000000 |

### Dense section-aware

| Metric | Development v1 | Remediated development v2 |
|---|---:|---:|
| Recall@k | 0.986111 | 0.986111 |
| MRR | 1.000000 | 1.000000 |
| nDCG@k | 0.959306 | 0.961115 |
| Citation readiness | 0.916667 | 1.000000 |
| Unsupported retrieval | 0.083333 | 0.025000 |
| Metadata violations | 0.000000 | 0.000000 |

## Resolved development failures

```text
dev-ret-023: Python SDK query no longer retrieves JavaScript setup guidance
dev-ret-024: JavaScript SDK query no longer retrieves Python setup guidance
```

No development-v2 case remains citation-unready for either remediated finalist.

## Causal interpretation

The algorithms and chunking candidates did not change.

The measured development changes are attributable to:

- a typed metadata overlay;
- exact applicability constraints;
- pre-ranking filtering.

They are not evidence that the underlying sparse or local dense scoring algorithm improved.

## Evidence integrity

The remediation report retains hashes for:

- source metadata registry;
- development v1;
- development v2;
- held-out v1;
- before scorecards;
- after scorecards;
- candidate manifests;
- case-result artifacts.

Held-out v1 remains unchanged with SHA-256:

```text
50f6b85d283598491708040f418e0b794736b551f3c2fd50a5b7531733c73477
```

## Non-claims

This report does not prove:

- held-out remediation success;
- Gate 1 completion;
- final retriever selection;
- model answer quality;
- actual model-generated citation support;
- production readiness.

## Next gate

Create held-out v2 with new wording and the same diagnostic boundaries:

- OAuth-grant separation;
- SDK-language separation;
- raw HTTP versus SDK interface separation;
- representation-format separation;
- unsupported-source control.

Held-out v2 must be frozen before the remediated candidates are scored.
