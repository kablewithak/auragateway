# Nimbus Relay Held-Out Retrieval v2 Constitution

## Status

```text
Version: 2.0.0
Status: frozen before candidate evaluation
Accepted cases: 12
Rejected proposals: 5
Top-k: 5
Metadata policy: authored-case-filters-v1
Promotion thresholds: unchanged from retrieval-development-selection-v1
```

## Purpose

Held-out v2 tests whether the typed retrieval metadata intervention generalizes beyond the development-v2 wording that motivated it.

It specifically exercises:

- OAuth client-credentials versus refresh-token applicability;
- Python versus JavaScript SDK applicability;
- raw HTTP versus SDK pagination;
- human-readable versus machine-readable event catalogues;
- stale versus current version conflicts;
- incomplete documentation boundaries;
- multi-source permission decisions.

## Freeze boundary

Before candidate scoring, the freeze record binds:

- accepted held-out v2 cases;
- rejected held-out v2 proposals;
- development v2;
- held-out v1 accepted cases and decision;
- the remediation report;
- the source-metadata registry.

Changing any bound artifact requires a new held-out version.

## Candidate boundary

Only the two remediated development-v2 finalists are admitted:

1. `bm25-fixed-window-remediated-v2`
2. `dense-hashed-tfidf-section-aware-remediated-v2`

Both use top-k five and the authored metadata policy.

## Decision rule

A candidate must pass every unchanged hard gate. Among passing candidates, selection uses:

1. final score descending;
2. Recall@k descending;
3. citation-support readiness descending;
4. unsupported-source retrieval ascending;
5. development rank ascending;
6. configuration ID ascending.

A composite score cannot override a failed hard gate.

## Privacy

The held-out artifacts contain synthetic queries and source identifiers only. Persisted results exclude retrieved document text.
