# Nimbus Relay Chunking Candidate Design

## Status

```text
Document version: 1.0.0
Phase: Phase 1 — Corpus, Retrieval, and Eval Asset Construction
Gate: Gate 1 — Retrieval Readiness
Candidate status: Generated and locally validated
Selected strategy: None
Retrieval claims permitted: No
```

## Purpose

AuraGateway must compare at least two chunking strategies before retrieval configuration is selected and frozen.

This document defines the two deterministic candidates used for development retrieval evaluation. It does not select a winner.

## Provider-neutral token unit

Both candidates use `lexical-whitespace-v1`.

A token is one non-whitespace span matched by `\S+`.

This is a deterministic local chunking unit. It is not a provider billing token, model tokenizer token, or cache-usage token.

The purpose is to keep chunk boundaries reproducible and provider-neutral while the development retrieval comparison is performed.

## Shared configuration

```text
Target lexical tokens: 96
Overlap lexical tokens: 16
Minimum trailing chunk size: 24
Corpus: Nimbus Relay 1.0.0
Source count: 30
```

Using the same target, overlap, and trailing-window rule reduces avoidable confounding between the two chunking candidates.

## Candidate A — Fixed Token Window

Configuration ID:

```text
fixed-window-v1
```

Behaviour:

- removes Markdown front matter;
- excludes JSON metadata and chunks only the `content` value;
- applies deterministic 96-token windows;
- applies 16-token overlap;
- shifts a short final window backwards instead of emitting a tiny fragment;
- stores complete source metadata on every chunk;
- does not preserve heading hierarchy.

This candidate tests a simple, portable baseline.

## Candidate B — Section Aware

Configuration ID:

```text
section-aware-v1
```

Behaviour:

- removes Markdown front matter;
- detects Markdown headings from levels one through six;
- stores the complete parent-heading path on each chunk;
- creates JSON sections from canonically sorted top-level `content` keys;
- emits a section directly when it fits within the target;
- uses the same bounded fixed-window fallback when a section exceeds the target;
- stores complete source metadata on every chunk.

Parent headings are retained as typed metadata rather than injected synthetic prose into source content.

## Determinism and identifiers

Every candidate has a canonical configuration SHA-256.

Every chunk ID is derived from:

- source ID;
- configuration SHA-256;
- source-local chunk index;
- parent-heading path;
- content SHA-256.

Candidate outputs are stored as deterministic JSON Lines with a typed manifest containing:

- corpus identity;
- source-manifest SHA-256;
- configuration;
- configuration SHA-256;
- chunk-output SHA-256;
- source-document count;
- chunk count;
- total lexical tokens;
- per-source chunk counts.

## Required negative controls

The verification suite must reject:

- modified chunk bytes;
- modified candidate manifests;
- changed frozen corpus bytes;
- changed corpus source manifest;
- duplicate chunk identifiers;
- missing candidate output;
- invalid configuration windows;
- fixed-window chunks containing parent headings;
- section-aware configuration that disables heading preservation.

## Selection boundary

Neither candidate is selected by implementation elegance or chunk count alone.

Selection requires development retrieval cases and reports for:

- Recall@k;
- Precision@k;
- MRR;
- correct-source-in-top-k rate;
- unsupported-source retrieval rate;
- stale-source retrieval rate;
- metadata-filter violations;
- near-duplicate displacement.

Held-out retrieval cases must not be used to tune these candidates.

## Current evidence boundary

This slice may claim:

- both required chunking strategies exist;
- both run over all 30 frozen sources;
- outputs are deterministic and hash-verifiable;
- source metadata is preserved;
- section headings are retained as typed metadata;
- bounded fallback splitting is implemented.

It may not claim:

- one strategy is better;
- retrieval quality is acceptable;
- dense or sparse retrieval readiness;
- Gate 1 completion.
