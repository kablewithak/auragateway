# Nimbus Relay Sparse Retrieval Candidate Report

## Status

```text
Report version: 1.0.0
Corpus: Nimbus Relay 1.0.0
Retriever: deterministic BM25 v1
Candidate status: locally validated
Selection decision: none
```

## Shared BM25 configuration

```text
Tokenizer: unicode-alnum-casefold-v1
k1: 1.2
b: 0.75
Default top-k: 5
Positive IDF: enabled
Zero-score hits: excluded
Metadata filters: applied before scoring
IDF population: complete chunking candidate
```

## Candidate statistics

| Metric | Fixed window | Section aware |
|---|---:|---:|
| Source documents | 30 | 30 |
| Chunks | 54 | 112 |
| Indexed terms | 4,386 | 3,920 |
| Vocabulary terms | 965 | 965 |
| Average chunk length | 81.222222222222 | 35.0 |
| Development smoke queries | 10 | 10 |

## Configuration fingerprints

### Fixed window

```text
Retrieval configuration:
14fe9392cca07a37ba9c754558ee03dc9120d36c35d87776bcb79a5a54bde0e0

Smoke result evidence:
c3045aaf51d44ad077e37047bbf468e4a8f70b5f141c682a36ca2c616718c00b
```

### Section aware

```text
Retrieval configuration:
1f1db39b8f2af5612e2c2a45cee5cc1dea3532444475ae70a365e8ade9ad7396

Smoke result evidence:
551a83133ebea9fab97d36a922bb44688c34a71306df390907308d754883369b
```

## Smoke behaviour

Both candidates returned the current source first for the following filtered development checks:

- API v2 key lifetime: `NR-AUTH-001`;
- webhook retry window: `NR-WEBHOOK-013`;
- idempotency retention after an ambiguous timeout: `NR-IDEM-020`;
- 409 versus 422 distinction: `NR-ERROR-012`;
- sandbox event-simulation gap: `NR-SANDBOX-029`.

When stale sources were intentionally included for the authentication conflict query, both candidates surfaced current and stale evidence in the top results.

This is useful diagnostic behaviour, but it is not a retrieval-quality score.

## Structural observations

The section-aware candidate has more than twice as many chunks and a substantially smaller average chunk length. It also preserves heading paths on hits.

The fixed-window candidate has fewer, larger chunks and therefore a smaller candidate set.

These structural differences may affect recall, precision, source diversity, latency, and evidence coherence. The current smoke queries are not sufficient to determine which trade-off is better.

## Validation

The implementation verifies:

- both frozen chunking candidates before indexing;
- typed chunk loading;
- deterministic Unicode tokenization;
- stable ranking and tie-breaking;
- metadata-filter behaviour;
- term-level contribution evidence;
- content-free persisted smoke results;
- retrieval manifest hashes;
- ranking-evidence hashes;
- rejection of modified manifests and smoke outputs.

## Decision

No chunking or retrieval candidate is selected.

The next decision input is a versioned development retrieval set with grounded relevance labels and explicit hard-case categories. That scorecard must measure retrieval quality before dense retrieval is compared.
