# Nimbus Relay Development Retrieval Recommendation

## Decision

```text
Status: development recommendation only
Recommended retriever: dense-hashed-tfidf-section-aware-v1
Recommended chunking: section-aware-v1
Recommended top-k: 5
Metadata policy: authored-case-filters-v1
Final score: 89.2954431949
Retrieval freeze permitted: no
Next required gate: held-out retrieval validation
```

## Why this candidate leads

Dense section-aware top-5 is the highest-scoring authored-policy variant that passes every hard gate.

It achieves:

```text
Mean Recall@k: 0.986111111111
All required sources in top-k: 1.000000000000
Citation-support readiness: 0.916666666667
MRR: 1.000000000000
nDCG@k: 0.959306224252
Unsupported-source retrieval: 0.083333333333
Failure-weighted case pass rate: 0.936507936508
```

It fails two development cases:

```text
dev-ret-023
dev-ret-024
```

Both are SDK-language contamination cases. The required language-specific source ranks first, but the
forbidden parallel-language SDK source also appears inside top five.

## Runner-up

```text
Retriever: bm25-fixed-window-v1
Top-k: 5
Final score: 89.0012929043
Margin: 0.2941502906
```

The margin is small. The recommendation is therefore fragile and must be confirmed on held-out cases.

BM25 fixed-window retains perfect development Recall@k, while dense section-aware leads on MRR, nDCG,
and unsupported-source noise.

## Passing authored-policy variants

| Rank | Variant | Top-k | Final score |
|---:|---|---:|---:|
| 1 | Dense section-aware | 5 | 89.2954431949 |
| 2 | BM25 fixed-window | 5 | 89.0012929043 |
| 3 | Dense section-aware | 7 | 86.8019080042 |
| 4 | BM25 section-aware | 7 | 86.7399551230 |

Top-3 variants can score well but fail one or more hard coverage gates. They are not promotable.

Top-7 variants recover coverage but pay a context-expansion and unsupported-source penalty.

## Metadata-policy finding

Metadata filters materially improve reliability.

At top-5, removing filter specificity causes:

- stale-source retrieval to rise above zero;
- unsupported-source retrieval to increase sharply;
- citation-support readiness to fall;
- additional failures in version-conflict, sandbox, and multi-source cases.

The recommendation therefore includes the authored metadata policy. The retriever alone is not the
complete retrieval contract.

## Evidence hashes

```text
Selection policy SHA-256:
9959710183212b57047da8a39af9ef8afbcc8c0af7f7b6b5f56e00a5831044e2

Variant results SHA-256:
8b8b9b8585292398ae89265e1e365ff19c832f1ba77c743450919b4742511e09

Selection report SHA-256:
3401519ef6ac55276cea3092e333fa014ad5a272734e1aa6ccd9b4dce22ecd76
```

## Required next step

Create and freeze a held-out retrieval set that is not derived from these 24 development cases.

The held-out gate must:

- evaluate the recommended dense section-aware top-5 configuration;
- retain BM25 fixed-window top-5 as the named challenger;
- preserve the same metric and filter contracts;
- include unseen paraphrases and failure combinations;
- block retrieval freeze if the recommendation does not remain eligible;
- report any recommendation reversal without hiding the development result.

## Evidence boundary

This result supports a development-only candidate recommendation.

It does not support retrieval freeze, Gate 1 completion, model answer quality, or measured A/B/C
execution.
