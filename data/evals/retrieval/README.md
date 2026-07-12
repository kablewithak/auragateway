# Nimbus Relay Retrieval Evaluation Assets

This directory contains the versioned retrieval-evaluation boundary for AuraGateway.

## Development set

```text
development-v1/
  accepted_cases.json
  rejected_cases.json
  bm25-fixed-window-v1/
    case_results.jsonl
    scorecard.json
  bm25-section-aware-v1/
    case_results.jsonl
    scorecard.json
  dense-hashed-tfidf-fixed-window-v1/
    case_results.jsonl
    scorecard.json
  dense-hashed-tfidf-section-aware-v1/
    case_results.jsonl
    scorecard.json
```

The accepted set contains exactly 24 grounded diagnostic cases.

Every accepted case records:

- a concrete failure hypothesis;
- source-level graded relevance judgments;
- required and forbidden source IDs;
- optional near-duplicate displacement sources;
- metadata filters;
- expected terminal decision;
- required information gain;
- acceptable variants;
- failure labels;
- acceptance and difficulty reasons;
- the development split identity.

Rejected proposed cases remain versioned with explicit reasons such as ambiguity, duplication, weak
diagnostic value, lack of grounding, or privacy risk.

## Development selection

```text
selection-v1/
  policy.json
  variants.jsonl
  report.json
```

The selection harness evaluates four retriever and chunking candidates across:

- top-k 3, 5, and 7;
- authored metadata filters;
- API-area-only negative control;
- no-metadata negative control.

Only authored-filter variants are recommendation eligible.

The report contains a development recommendation only. Retrieval freeze remains prohibited until a
separate held-out retrieval set validates the selected candidate.

## Evidence boundary

Persisted case results exclude raw query text and retrieved chunk content. They retain query hashes,
source and chunk identities, rankings, deterministic metrics, and failure evidence.

The four scorecards share the same frozen cases and metric contract. The selection artifacts preserve
all 36 variants, hard-gate outcomes, failure-weighted scores, rankings, and the development-only
recommendation.

No held-out retrieval cases are stored here.
