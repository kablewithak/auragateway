# Retrieval candidate artifacts

This directory contains deterministic development artifacts for AuraGateway retrieval candidates.

## BM25 v1

`bm25-v1/` contains one shared development-only smoke-query set and one candidate directory per chunking strategy:

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

The smoke results are content-free ranking evidence. They retain query hashes, source and chunk identifiers, scores, filters, and matched terms, but do not duplicate retrieved document text.

These artifacts prove deterministic index construction and ranking behaviour. They are not retrieval-quality evaluation results and must not be used to select a chunking strategy.
