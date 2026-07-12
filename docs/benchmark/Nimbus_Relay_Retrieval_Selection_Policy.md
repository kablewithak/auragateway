# Nimbus Relay Retrieval Development Selection Policy

## Status

```text
Policy version: retrieval-development-selection-v1
Status: development only
Held-out validation required: yes
Retrieval freeze permitted: no
Measured execution permitted: no
```

## Purpose

This policy compares the four current retrieval candidates without allowing one favourable metric to
hide missing required sources, stale-source leakage, filter violations, or near-duplicate displacement.

The selection is a development recommendation only. It cannot freeze the retrieval configuration.

## Compared candidates

- BM25 with fixed-window chunks
- BM25 with section-aware chunks
- deterministic local dense retrieval with fixed-window chunks
- deterministic local dense retrieval with section-aware chunks

## Variant sweep

Every candidate is evaluated at:

```text
Top-k: 3, 5, 7
```

Every top-k value is evaluated under:

```text
authored-case-filters-v1
api-area-only-negative-control-v1
no-metadata-negative-control-v1
```

Only `authored-case-filters-v1` variants may be recommended.

The other policies are negative controls showing what breaks when filter specificity is removed.

## Hard development gates

A recommendation-eligible variant must satisfy every gate:

| Gate | Threshold |
|---|---:|
| Mean Recall@k | at least 0.98 |
| Correct source in top-k | exactly 1.00 |
| All required sources in top-k | at least 0.95 |
| Citation-support readiness | at least 0.90 |
| Mean reciprocal rank | at least 0.95 |
| Failure-weighted case pass rate | at least 0.90 |
| Unsupported-source retrieval | at most 0.11 |
| Unwanted stale-source retrieval | exactly 0.00 |
| Metadata-filter violations | exactly 0.00 |
| Near-duplicate displacement | exactly 0.00 |

A higher composite score cannot override a failed hard gate.

## Failure-weighted case scoring

Case families receive different weights because failures have different operational consequences.

| Case family | Weight |
|---|---:|
| Version conflict | 3 |
| Similar error codes | 2 |
| Missing required parameters | 3 |
| Incomplete documentation | 3 |
| Near-duplicate displacement | 2 |
| Multi-source grounding | 3 |
| Metadata filtering | 3 |
| Unsupported behaviour | 3 |
| Exact procedure | 2 |
| SDK variant | 2 |

A case passes the failure-weighted gate only when it is citation-support ready:

- every required source is present;
- no forbidden source is present;
- no metadata-filter violation occurs.

## Benefit score

The positive score is a weighted sum:

| Metric | Weight |
|---|---:|
| Mean Recall@k | 0.20 |
| All required sources in top-k | 0.15 |
| Citation-support readiness | 0.20 |
| Mean reciprocal rank | 0.10 |
| Mean nDCG@k | 0.10 |
| Mean Precision@k | 0.05 |
| Failure-weighted case pass rate | 0.20 |

Weights sum to 1.00.

## Penalties

| Failure metric | Multiplier |
|---|---:|
| Unsupported-source retrieval | 0.20 |
| Unwanted stale-source retrieval | 0.25 |
| Metadata-filter violations | 0.30 |
| Near-duplicate displacement | 0.20 |

Top-k also incurs a context-expansion penalty:

```text
0.01 for every returned slot above top-3
```

This prevents top-7 from winning merely by retrieving more context.

## Ranking rule

Authored-policy variants are ranked by:

1. hard-gate pass before hard-gate failure;
2. final score descending;
3. smaller top-k;
4. retriever configuration ID.

## Non-claims

This policy does not prove:

- held-out retrieval quality;
- final retrieval readiness;
- model answer quality;
- actual citation support;
- production readiness;
- superiority outside the frozen Nimbus Relay development workload.
