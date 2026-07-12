# Nimbus Relay Dense Retrieval Development Report

## Decision status

```text
Dense candidates: Locally validated
Development scorecards: Locally validated
Retrieval selection: Not made
Gate 1: Open
```

The deterministic local dense baseline was evaluated against the same 24 accepted development cases
and source-level metric contract used for BM25.

## Candidate construction

| Candidate | Chunks | Vocabulary | Dimensions | Mean non-zero dimensions |
|---|---:|---:|---:|---:|
| Dense fixed-window | 54 | 3,986 | 384 | 112.314814814815 |
| Dense section-aware | 112 | 3,906 | 384 | 55.732142857143 |

Configuration fingerprints:

```text
dense-hashed-tfidf-fixed-window-v1
200a10f87d39b09cc2e9550706d17d9c3bbec286c40c64d46ff61d6804d018e5

dense-hashed-tfidf-section-aware-v1
2741ca603cf7a2a009e6d4143a882eefee119544376f1c2d4272b64400064f0f
```

## Four-candidate development comparison

| Metric | BM25 fixed | BM25 section | Dense fixed | Dense section |
|---|---:|---:|---:|---:|
| Recall@k | **1.000000** | 0.972222 | 0.986111 | 0.986111 |
| Precision@k | **0.325000** | 0.308333 | 0.316667 | 0.316667 |
| MRR | 0.972222 | 0.972222 | 0.979167 | **1.000000** |
| nDCG@k | 0.956280 | 0.941375 | 0.948134 | **0.959306** |
| Correct source in top-k | 1.000000 | 1.000000 | 1.000000 | 1.000000 |
| All required sources in top-k | **1.000000** | 0.958333 | 0.958333 | **1.000000** |
| Citation-support readiness | **0.916667** | 0.875000 | 0.875000 | **0.916667** |
| Unsupported-source retrieval | 0.098611 | **0.075000** | 0.106944 | 0.083333 |
| Unwanted stale-source retrieval | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| Metadata-filter violations | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| Near-duplicate displacement | 0.000000 | 0.000000 | 0.000000 | 0.000000 |

## Diagnostic findings

### Dense section-aware strengths

Dense section-aware has:

- the best MRR;
- the best nDCG@k;
- complete required-source coverage across all 24 cases;
- citation-support readiness equal to BM25 fixed-window;
- less unsupported-source noise than dense fixed-window.

This is meaningful development evidence, not a final promotion decision.

### Dense fixed-window permission failure

Dense fixed-window misses `NR-PERM-027`, the role-permission matrix, in `dev-ret-008`.

The case retrieves:

- the general error reference;
- the custom-role guide;
- the similar 409-versus-422 guide.

The required role matrix does not enter top five. This reduces recall, all-required-source coverage,
and citation-support readiness.

### Shared SDK-language contamination

Both dense candidates retrieve the forbidden parallel-language SDK source inside top five for:

- `dev-ret-023`, where Python is required and JavaScript is forbidden;
- `dev-ret-024`, where JavaScript is required and Python is forbidden.

The correct SDK source ranks first in both cases, but the forbidden source blocks citation-support
readiness.

This failure is shared with the BM25 candidates and likely requires stronger query or metadata routing,
not merely a retriever-family change.

## Selection interpretation

No candidate dominates every development metric.

- BM25 fixed-window has the only perfect Recall@k.
- Dense section-aware has the strongest MRR and nDCG@k.
- BM25 fixed-window and dense section-aware tie on citation-support readiness.
- BM25 section-aware has the lowest unsupported-source rate.

Therefore the next step is a versioned selection policy that weighs required-source coverage,
citation-support readiness, unsupported-source noise, maintainability, and later held-out performance.

## Evidence boundary

This report supports:

- deterministic local dense candidate construction;
- four-way development comparison under shared cases and metrics;
- identified candidate-specific and shared failure modes;
- provider-neutral dense adapter readiness.

It does not support:

- a claim that hashed TF-IDF equals neural embeddings;
- final retrieval or chunking selection;
- held-out quality;
- production vector-store readiness;
- model-answer quality;
- Gate 1 completion.

## Commercial proof angle

This artifact demonstrates a RAG Reliability Sprint behaviour a CTO can inspect:

- candidates are compared on fixed cases;
- failures remain visible;
- algorithm changes do not bypass the same metric contract;
- development gains do not trigger promotion without held-out evidence.
