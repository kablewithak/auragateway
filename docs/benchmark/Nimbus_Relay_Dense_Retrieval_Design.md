# Nimbus Relay Deterministic Local Dense Retrieval Design

## Status

```text
Design version: 1.0.0
Phase: Phase 1 — Corpus, Retrieval, and Eval Asset Construction
Proof gate: Gate 1 — Retrieval Readiness
Candidate status: Development candidate
External model download: None
Network dependency: None
```

## Purpose

This design introduces a provider-neutral dense retrieval baseline over both frozen chunking
candidates.

The baseline exists to answer a narrow diagnostic question:

> Does a deterministic dense-vector representation change source ranking behaviour relative to BM25
> under the same corpus, chunking candidates, filters, top-k, development cases, and metric contract?

It is not intended to imitate a production neural embedding service.

## Architecture decision

The initial dense encoder is `hashed-tfidf-dense-v1`.

It is used because it is:

- deterministic across runs;
- local-first;
- provider-neutral;
- free of model-download and network requirements;
- inspectable at the vector-construction boundary;
- suitable for testing dense-index contracts, filters, ranking, traces, manifests, and eval plumbing.

A neural embedding adapter remains a later extension seam. It must use the same typed retrieval and
evaluation boundaries rather than bypassing them.

## Vector construction

The encoder applies:

```text
Tokenizer: unicode-alnum-casefold-v1
Features: token unigrams and token bigrams
Term frequency: sublinear, 1 + log(tf)
IDF: log((N + 1) / (df + 1)) + 1
Feature hashing: SHA-256 signed bucket assignment
Vector dimension: 384
Normalization: L2
Similarity: cosine
```

Features absent from the indexed vocabulary are ignored when encoding a query. A query that produces
an empty vector returns no hits rather than fabricated zero-score results.

Hash collisions are possible and are part of this candidate's known limitations. Signed hashing
reduces systematic positive collision bias but does not eliminate collisions.

## Index and query policy

- IDF is calculated over the complete chunking candidate.
- Metadata filters are applied before similarity scoring.
- Only positive cosine-similarity results are eligible.
- Scores are rounded to 12 decimal places.
- Default top-k is five.
- Ranking ties use source ID, chunk index, and chunk ID.
- The same configuration is applied to fixed-window and section-aware chunks.

## Typed evidence

Every runtime dense hit contains:

- source and chunk provenance;
- lifecycle and stale status;
- source version;
- API area;
- parent headings;
- content hash;
- cosine similarity;
- query non-zero dimension count;
- chunk non-zero dimension count;
- shared non-zero dimension count.

Persisted smoke evidence removes chunk content and does not persist vectors.

The manifest binds:

- dense configuration and fingerprint;
- chunking manifest and chunk hashes;
- smoke-query hash;
- smoke-result hash;
- vocabulary size;
- vector dimension;
- average non-zero dimensions;
- source and chunk counts.

## Privacy and security boundary

The implementation:

- requires no credentials;
- sends no data to an external provider;
- persists no raw dense vectors;
- persists no raw development queries in result artifacts;
- persists no duplicate document content in scorecards;
- rejects changed upstream chunk artifacts;
- emits typed safe error envelopes.

## Failure taxonomy

The dense runner blocks on:

- missing or invalid chunking artifacts;
- unsupported chunking configuration;
- malformed dense configuration;
- empty feature vocabulary;
- empty chunk vectors;
- invalid manifests;
- changed smoke-result bytes;
- changed manifest bytes;
- changed upstream chunk bytes.

## Known limitations

This candidate is lexical-statistical despite producing dense vectors.

It does not provide:

- neural semantic embeddings;
- multilingual semantic alignment;
- synonym understanding beyond shared features;
- learned domain representations;
- proof of hosted vector-store behaviour;
- proof of production embedding quality.

These limits are retained in the report and prevent overstating the candidate as a neural dense
retriever.
