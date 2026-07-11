# Nimbus Relay Chunking Candidate Report

## Status

```text
Report version: 1.0.0
Corpus: Nimbus Relay 1.0.0
Corpus source-manifest SHA-256: c68212afd5381dec8bce49d0d5fee231a3b5589bf5460c0f72297e0c84422f55
Candidate state: Locally validated
Selection decision: Not made
Gate 1: Open
```

## Candidate summary

| Candidate | Sources | Chunks | Total lexical tokens | Median tokens | Maximum tokens | Parent headings |
|---|---:|---:|---:|---:|---:|---:|
| Fixed window v1 | 30 | 54 | 4,253 | 85.0 | 96 | 0 |
| Section aware v1 | 30 | 112 | 3,805 | 30.5 | 73 | 112 |

These figures describe generated chunk shape only. Lower token volume or fewer chunks is not treated as better retrieval performance.

## Fixed-window evidence

```text
Configuration ID: fixed-window-v1
Configuration SHA-256: 94dc0f27358db477d667cb579ef8719652e30d10b6095fe0965315cb6533316e
Chunks SHA-256: 7e0498dabddbd87816c55aff1789aff2c79dde3ae742aee3d30b7cad6ac61842
Chunk count: 54
Total lexical tokens: 4,253
Token range: 20–96
```

The 20-token minimum observed chunk is a naturally short source document. The 24-token minimum is a fallback-window rule, not a padding requirement.

## Section-aware evidence

```text
Configuration ID: section-aware-v1
Configuration SHA-256: cf19844c80542b55747f96e0019f3b340456bd9156672ceb5fee8939c1a6b7c3
Chunks SHA-256: 7a17234f988fc3538f7fd959c1174e362dcc621569d7fdbdda87f577b334fa0f
Chunk count: 112
Total lexical tokens: 3,805
Token range: 4–73
Chunks with parent-heading metadata: 112
```

Naturally short semantic sections remain separate. Small JSON scalar fields are grouped into a deterministic `document_fields` section rather than emitted as unrelated one-field fragments.

## Deterministic controls

Both candidates:

- verify the frozen corpus before chunking;
- exclude Markdown front matter from retrieval content;
- exclude JSON metadata and chunk only the `content` value;
- preserve source lifecycle and diagnostic metadata;
- use canonical configuration hashes;
- derive stable chunk IDs from source, configuration, index, heading path, and content hash;
- produce typed JSON Lines;
- produce typed manifests with source counts and content hashes;
- reject modified output or manifest bytes;
- reject a changed frozen corpus.

## Structural contrast

The candidate difference is intentional:

- fixed window prioritizes simple, consistently sized lexical windows;
- section aware prioritizes semantic boundaries and heading provenance, using bounded fallback windows only for oversized sections.

The two strategies use the same target and overlap values so the later retrieval comparison focuses on structural segmentation rather than unrelated window settings.

## Selection gate

No strategy is selected in this report.

Selection requires fixed development retrieval cases and comparison of:

- Recall@k;
- Precision@k;
- MRR;
- correct-source-in-top-k rate;
- unsupported-source retrieval rate;
- stale-source retrieval rate;
- metadata-filter violation rate;
- near-duplicate displacement rate.

The held-out retrieval set may confirm the frozen choice but may not tune it.

## Current claim

AuraGateway now has two deterministic, provider-neutral chunking candidates over the complete frozen corpus.

It does not yet have evidence that either candidate is retrieval-superior or Gate 1 ready.
