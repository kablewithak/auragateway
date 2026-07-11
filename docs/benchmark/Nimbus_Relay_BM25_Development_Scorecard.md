# Nimbus Relay BM25 Development Retrieval Scorecard

## Status

```text
Evaluation split: development
Accepted cases: 24
Candidates: 2 sparse BM25 candidates
Selection decision: not made
Dense comparison: not yet available
Gate 1: open
```

## Metric contract

Metrics use `source-level-retrieval-metrics-v1`.

The retriever still returns chunks. Metrics deduplicate source identities where duplicate chunks could
inflate apparent coverage.

### Recall@k

Number of distinct relevant sources retrieved divided by the number of labelled relevant sources.

### Precision@k

Number of distinct relevant sources retrieved divided by the configured `k`.

Duplicate chunks from the same relevant source do not add precision credit.

### MRR

Reciprocal rank of the first hit from any labelled relevant source.

### nDCG@k

Uses graded source relevance. The first occurrence of a source receives its labelled gain; later chunks
from the same source receive zero gain.

### Correct-source-in-top-k rate

Rate of cases where at least one required source appears in the top-k result.

### All-required-sources-in-top-k rate

Rate of cases where every required source appears in the top-k result.

### Citation-support readiness rate

Rate of cases where:

- every required source is present;
- no forbidden source is present;
- no metadata-filter violation occurs.

This is retrieval readiness for later citation construction. It is not a citation-support claim about
model output.

### Unsupported-source retrieval rate

Mean case-level rate of hit slots whose source has no relevance judgment.

### Stale-source retrieval rate

Mean case-level rate of stale hit slots that were not deliberately labelled as relevant conflict
evidence.

Stale sources required to explain a version conflict do not count as unwanted stale retrieval.

### Metadata-filter violation rate

Mean case-level rate of returned chunks that violate the case's typed filter.

### Near-duplicate displacement rate

Rate of near-duplicate cases where the lower-priority paired source ranks before the required source.

## Results

| Metric | Fixed window + BM25 | Section aware + BM25 |
|---|---:|---:|
| Cases | 24 | 24 |
| Mean Recall@k | 1.000000 | 0.972222 |
| Mean Precision@k | 0.325000 | 0.308333 |
| MRR | 0.972222 | 0.972222 |
| Mean nDCG@k | 0.956280 | 0.941375 |
| Correct source in top-k | 1.000000 | 1.000000 |
| All required sources in top-k | 1.000000 | 0.958333 |
| Citation-support readiness | 0.916667 | 0.875000 |
| Unsupported-source retrieval | 0.098611 | 0.075000 |
| Unwanted stale-source retrieval | 0.000000 | 0.000000 |
| Metadata-filter violations | 0.000000 | 0.000000 |
| Near-duplicate displacement | 0.000000 | 0.000000 |

## Diagnostic findings

### Shared SDK-language contamination

Both candidates retrieve the wrong-language SDK source inside top five for:

- the Python configuration case;
- the JavaScript configuration case.

The required language-specific source ranks first, so first-hit metrics remain strong. However, the
forbidden parallel-language source prevents citation-support readiness.

This is a real retrieval-noise failure, not a reason to weaken the case.

### Section-aware permission coverage failure

The section-aware candidate misses `NR-PERM-027`, the role-permission matrix, in the multi-source 403
case.

It retrieves the generic error source and multiple custom-role-guide chunks, but the role matrix does
not enter top five. This causes:

- one incomplete required-source case;
- lower Recall@k;
- lower all-required-source coverage;
- lower citation-support readiness.

### Strengths shared by both candidates

Both candidates achieve:

- required-source presence in top five for all 24 cases;
- zero metadata-filter violations;
- zero unwanted stale-source retrieval;
- zero near-duplicate displacement across four paired cases;
- identical MRR.

## Interpretation

The fixed-window BM25 candidate is stronger on this development set, particularly for multi-source
coverage and citation-support readiness.

No configuration is selected or frozen because:

- the dense retrieval candidate does not exist yet;
- hybrid retrieval has not been evaluated;
- top-k and filter policy have not been compared across retrieval types;
- held-out retrieval cases remain protected and unused.

## Hash evidence

```text
Accepted development set SHA-256:
49d5e9055b7b00bcfdf5f9dc932c836a844c37f835709d0d376d38285934e342

Rejected candidate set SHA-256:
d8c844cf7c2e203823e56ff1b94ce920989519147f890b9cedd501df64189e58

Fixed-window case results SHA-256:
1abfd3bbc28b220e30af88e87c89d008ef79b1a4c4102fffb34ef5782fed9915

Section-aware case results SHA-256:
a098bbd09d62d501384f174e23b163b67b8fbb2b0afe194219d86a04a649f3f6
```

## Non-claims

This scorecard does not prove:

- held-out retrieval quality;
- dense retrieval quality;
- hybrid superiority;
- final chunking selection;
- retrieval freeze readiness;
- model answer quality;
- actual citation support;
- Gate 1 completion.
