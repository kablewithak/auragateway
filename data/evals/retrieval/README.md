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

## Evidence boundary

Persisted case results exclude raw query text and retrieved chunk content. They retain query hashes,
source and chunk identities, rankings, deterministic metrics, and failure evidence.

The four scorecards share the same frozen cases and metric contract. They remain development evidence;
no held-out retrieval cases are stored here. Held-out assets must be created and frozen only after a
retrieval configuration is selected.
