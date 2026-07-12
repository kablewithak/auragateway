# Nimbus Relay Gate 1 Retrieval Freeze Report

## Decision

```text
Gate: Gate 1 — Retrieval Readiness
Decision: PASS
Development-v2 recommendation: BM25 fixed-window remediated v2
Held-out-v2 selection: dense section-aware remediated v2
Outcome: development ranking reversed
Top-k: 5
Metadata policy: authored-case-filters-v1
Configuration fingerprint:
220ce9ac6e19789bedf1aedc2b6253db5ba03a09ebcc6efdac203eb80cd23490
Measured runtime execution permitted: no
```

## Held-out v2 results

| Metric | BM25 fixed-window v2 | Dense section-aware v2 |
|---|---:|---:|
| Recall@k | 1.000000 | 1.000000 |
| Precision@k | 0.233333 | 0.233333 |
| MRR | 1.000000 | 1.000000 |
| nDCG@k | 0.963743 | 0.977577 |
| All required sources | 1.000000 | 1.000000 |
| Citation readiness | 1.000000 | 1.000000 |
| Unsupported retrieval | 0.000000 | 0.000000 |
| Stale retrieval | 0.000000 | 0.000000 |
| Metadata violations | 0.000000 | 0.000000 |
| Near-duplicate displacement | 0.000000 | 0.000000 |
| Final score | 93.804100 | 93.942441 |

Both finalists pass every hard gate. Dense section-aware wins by `0.138340639600` because of stronger held-out nDCG.

## Frozen retrieval contract

```text
Retriever: dense-hashed-tfidf-section-aware-remediated-v2
Chunking: section-aware-v1
Top-k: 5
Metadata overlay: nimbus-relay-retrieval-metadata-v1
Metadata policy: authored-case-filters-v1
```

The freeze binds:

- frozen corpus manifest;
- section-aware chunking manifest;
- remediated dense retrieval manifest;
- source-metadata registry;
- remediation report;
- held-out v2 cases and selected scorecard;
- selection policy;
- Gate 1 decision.

## Evidence boundary

This proves retrieval readiness for the named synthetic Nimbus Relay workload and frozen configuration.

It does not prove model answer quality, actual model-generated citation support, provider runtime readiness, cache behavior, or production readiness.

## Next gate

Gate 2 requires the 18 multi-turn diagnostic episode set, terminal output schemas, failure labels, and fixed quality-evaluation assets.
