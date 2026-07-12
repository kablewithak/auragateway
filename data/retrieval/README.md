# Retrieval candidate artifacts

This directory contains deterministic development artifacts for AuraGateway retrieval candidates.

## BM25 v1

`bm25-v1/` contains one shared development-only smoke-query set and one candidate directory per
chunking strategy:

```text
bm25-v1/
├── smoke_queries.json
├── fixed-window-v1/
│   ├── manifest.json
│   └── smoke_results.jsonl
└── section-aware-v1/
    ├── manifest.json
    └── smoke_results.jsonl
```

## Hashed TF-IDF dense v1

`hashed-tfidf-dense-v1/` applies the same smoke queries to deterministic local dense vectors:

```text
hashed-tfidf-dense-v1/
├── fixed-window-v1/
│   ├── manifest.json
│   └── smoke_results.jsonl
└── section-aware-v1/
    ├── manifest.json
    └── smoke_results.jsonl
```

The dense baseline uses hashed TF-IDF vectors, not a neural embedding model. It is a local,
provider-neutral diagnostic baseline designed for deterministic comparison without model downloads,
network calls, or external vector infrastructure.

## Evidence boundary

Smoke results are content-free ranking evidence. They retain query hashes, source and chunk
identifiers, scores, filters, and algorithm-specific scoring evidence, but do not duplicate retrieved
document text or persist vectors.

These artifacts prove deterministic candidate construction and ranking behaviour. They are not held-out
retrieval-quality evidence and do not select a winning strategy.

## Metadata remediation v1

`remediation-v1/source_metadata.json` is a typed, hash-bound applicability overlay for the frozen
corpus. It adds language, interface, OAuth-grant, and representation discriminators without changing
corpus or chunk bytes.

The overlay is used only by versioned remediated candidates. Existing v1 retrieval artifacts remain
reproducible.
