# Nimbus Relay Sparse Retrieval Design

## Status

```text
Document version: 1.0.0
Phase: 1 — Corpus, Retrieval, and Eval Asset Construction
Proof gate: Gate 1 — Retrieval Readiness
Retriever: BM25 candidate baseline
Selection status: Not selected
```

## Purpose

This design defines the deterministic sparse retrieval baseline used to compare the two frozen Nimbus Relay chunking candidates.

The implementation is intentionally local, dependency-light, and provider-neutral. It establishes a reproducible lexical baseline before dense retrieval is introduced.

## Candidate matrix

The same BM25 policy is applied to both chunking candidates:

| Retrieval configuration | Chunking input |
|---|---|
| `bm25-fixed-window-v1` | `fixed-window-v1` |
| `bm25-section-aware-v1` | `section-aware-v1` |

Keeping BM25 parameters constant isolates chunking differences during later retrieval evaluation.

## Tokenization

Tokenizer ID:

```text
unicode-alnum-casefold-v1
```

Rules:

1. normalize text with Unicode NFKC;
2. apply Unicode case folding;
3. extract lowercase ASCII alphanumeric terms using `[a-z0-9]+`;
4. do not stem;
5. do not remove stop words;
6. do not use provider or model tokenizers.

These terms are retrieval units only. They are not billing tokens or model context tokens.

## BM25 policy

```text
Algorithm: BM25
k1: 1.2
b: 0.75
IDF: log(1 + (N - df + 0.5) / (df + 0.5))
Default top-k: 5
Score precision: 12 decimal places
Minimum returned score: greater than 0
```

Query-term frequency contributes multiplicatively. IDF statistics are calculated over the complete chunking candidate.

## Metadata filters

Filters are typed and applied before chunk scoring.

Supported filters:

- API area;
- source lifecycle status;
- source completeness;
- explicit source ID;
- stale-source policy: include, exclude, or stale-only;
- version-sensitive procedures only.

Global candidate IDF remains fixed when filters are applied. This prevents the same query term from receiving different IDF values merely because an operator changed a metadata filter.

## Ranking and tie-breaking

Only positive-score chunks are returned.

Ranking order is:

1. rounded BM25 score descending;
2. source ID ascending;
3. source-local chunk index ascending;
4. chunk ID ascending.

This ordering is deterministic and avoids dependence on dictionary iteration, filesystem order, or insertion timing.

## Result contracts

The runtime retrieval result contains:

- query ID and SHA-256 fingerprint;
- retrieval and chunking configuration identifiers;
- applied filters;
- eligible candidate count;
- positive-score count;
- ranked chunks with content;
- source and lifecycle provenance;
- heading provenance;
- matched terms;
- term-level BM25 contributions.

Persisted smoke evidence removes chunk content. Public or normal runtime traces must not log raw query or retrieved content.

## Candidate manifests

Every candidate manifest binds:

- retrieval configuration and SHA-256;
- chunking manifest and SHA-256;
- chunk JSONL and SHA-256;
- smoke-query set and SHA-256;
- smoke-result evidence and SHA-256;
- source count;
- chunk count;
- indexed token count;
- vocabulary size;
- average chunk length.

Candidate verification rebuilds all index statistics and smoke rankings from the frozen chunk artifacts.

## Failure controls

The retrieval runner blocks when:

- a chunking candidate fails deterministic verification;
- a chunk fails typed validation;
- a chunk references the wrong chunking configuration;
- the smoke-query set is missing, malformed, or contains duplicate IDs;
- persisted ranking evidence changes;
- a retrieval manifest changes;
- required candidate artifacts are missing.

## Development smoke queries

The ten development-only smoke queries cover:

- current versus stale authentication guidance;
- webhook retry windows;
- idempotency replay after ambiguous timeout;
- OAuth refresh errors;
- pagination;
- retry and rate-limit guidance;
- similar error codes;
- permissions;
- an intentionally incomplete sandbox capability question.

They demonstrate execution and metadata filters. They are not the development retrieval scorecard and are not held out.

## Evidence boundary

This implementation proves:

- deterministic BM25 indexing;
- typed metadata filtering;
- stable tie-breaking;
- positive-score-only result handling;
- content-free persisted evidence;
- deterministic candidate verification.

It does not prove:

- Recall@k, Precision@k, MRR, or nDCG;
- chunking superiority;
- dense retrieval quality;
- held-out performance;
- Gate 1 completion.
