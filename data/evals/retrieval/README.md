# Nimbus Relay Retrieval Evaluation Assets

This directory contains the versioned retrieval-evaluation boundary for AuraGateway.

## Development set

```text
development-v1/
  accepted_cases.json
  rejected_cases.json
  <retriever-config-id>/
    case_results.jsonl
    scorecard.json
```

The accepted development set contains exactly 24 grounded diagnostic cases.

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
- the protected split identity.

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

## Held-out validation

```text
held-out-v1/
  accepted_cases.json
  rejected_cases.json
  freeze_record.json
  policy.json
  <finalist-config-id>/
    case_results.jsonl
    scorecard.json
  decision.json
```

Held-out v1 contains 12 accepted cases and five rejected proposals. The set and comparison policy were
hash-frozen before finalist scoring.

The current Gate 1 decision is blocked:

```text
Passing finalists: 0 / 2
Selected retriever: none
Retrieval freeze permitted: no
```

Held-out v1 must not be edited in response to the result. Remediation requires a new held-out version.

## Evidence boundary

Persisted case results exclude raw query text and retrieved chunk content. They retain query hashes,
source and chunk identities, rankings, deterministic metrics, and failure evidence.

The development artifacts preserve all 36 variants and the development-only recommendation. The
held-out artifacts preserve both finalist scorecards, frozen hard-gate outcomes, and the blocked Gate 1
decision.

No retrieval configuration is frozen.

## Development remediation

```text
development-v2/
  accepted_cases.json
  rejected_cases.json

remediation-v1/
  <remediated-config-id>/
    manifest.json
    case_results.jsonl
    scorecard.json
  report.json
```

Development v2 applies typed source-applicability filters to seven existing diagnostic cases. The
before/after report preserves development v1 and held-out v1 hashes.

Gate 1 remains blocked until a separately authored and frozen held-out v2 confirms the remediation.

## Held-out v2

Held-out v2 validates the metadata-remediated finalists under unchanged Gate 1 thresholds. Both pass; dense section-aware is selected and the development-v2 BM25 ranking is reversed.
