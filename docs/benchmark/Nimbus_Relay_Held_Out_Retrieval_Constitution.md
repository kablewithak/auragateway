# Nimbus Relay Held-Out Retrieval Constitution

## Status

```text
Version: 1.0.0
State: frozen before candidate evaluation
Evaluation split: held_out
Accepted cases: 12
Rejected proposals: 5
Finalists: 2
Top-k: 5
Metadata policy: authored-case-filters-v1
```

## Purpose

The held-out retrieval set tests whether the development recommendation survives new diagnostic wording and source combinations without changing the corpus, chunking outputs, retriever implementations, metric contract, selection thresholds, or metadata policy.

The held-out set is not a second development set. Its cases may not be edited in response to candidate results. Any remediation requires a new versioned held-out set and invalidates the current Gate 1 decision.

## Frozen inputs

The held-out freeze record binds:

- the 12 accepted cases;
- the five rejected proposals;
- the 24-case development set;
- the development selection policy;
- the development selection report;
- the two rank-one and rank-two finalists;
- each finalist retrieval manifest and configuration hash.

The freeze record declares that authoring completed before candidate results were generated.

## Finalists

### Development rank 1

```text
Retriever: dense-hashed-tfidf-section-aware-v1
Chunking: section-aware-v1
Top-k: 5
Metadata policy: authored-case-filters-v1
Development score: 89.2954431949
```

### Development rank 2

```text
Retriever: bm25-fixed-window-v1
Chunking: fixed-window-v1
Top-k: 5
Metadata policy: authored-case-filters-v1
Development score: 89.0012929043
```

No third candidate may enter held-out evaluation without creating a new held-out policy version.

## Case design

The accepted cases cover:

- current-versus-stale rate-limit guidance;
- OAuth grant-type separation;
- upload-specific and general retry evidence;
- raw HTTP versus SDK pagination;
- webhook signature plus event-state grounding;
- endpoint migration plus explicit versioning;
- incomplete multipart capability evidence;
- custom-role restrictions plus propagation time;
- current-versus-legacy sandbox limits;
- machine-readable versus prose event catalogues;
- SDK language isolation;
- idempotency replay plus retry safety.

Each case stores:

- a concrete failure hypothesis;
- source-level graded relevance;
- required and forbidden sources;
- near-duplicate displacement sources where applicable;
- expected terminal decision;
- required information gain;
- acceptable variants;
- failure labels;
- acceptance and difficulty reasons.

## Rejected proposals

Rejected cases retain explicit reasons for:

- triviality;
- duplication;
- missing corpus grounding;
- privacy-unsafe production actions;
- ambiguity.

Rejected proposals are evidence that the held-out set was curated for diagnostic value rather than case count.

## Split protection

The harness rejects:

- development-style case IDs inside the held-out split;
- held-out-style case IDs inside the development split;
- exact query duplication across development and held-out sets;
- unknown source references;
- rejected duplicate cases pointing to unknown accepted held-out cases;
- any changed byte after the held-out freeze hash was recorded.

## Decision rule

The development recommendation is not auto-confirmed.

Gate 1 selects the highest-scoring finalist that passes every frozen hard gate. Ranking uses:

1. final score descending;
2. Recall@k descending;
3. citation-support readiness descending;
4. unsupported-source retrieval ascending;
5. development rank ascending;
6. retriever configuration ID ascending.

If no finalist passes every hard gate:

- Gate 1 is blocked;
- no retrieval freeze manifest may exist;
- measured runtime execution remains prohibited;
- remediation requires a new held-out version.

## Hard gates

The held-out comparison inherits the development selection thresholds:

```text
Recall@k: >= 0.98
Correct source in top-k: >= 1.00
All required sources in top-k: >= 0.95
Citation-support readiness: >= 0.90
MRR: >= 0.95
Failure-weighted case pass rate: >= 0.90
Unsupported-source retrieval: <= 0.11
Unwanted stale-source retrieval: <= 0.00
Metadata-filter violations: <= 0.00
Near-duplicate displacement: <= 0.00
```

Composite scoring cannot override a failed hard gate.

## Evidence boundary

The held-out run can support a retrieval-freeze decision only.

It cannot establish:

- answer-generation quality;
- actual citation support in model output;
- provider telemetry integrity;
- runtime latency or cost improvement;
- measured A/B/C execution readiness;
- production readiness.
