# Nimbus Relay Synthetic Corpus Constitution

## Document control

```text
Version: 1.0.0
Status: Frozen
Freeze date: 2026-07-12
Benchmark Constitution dependency: 1.0.0
Corpus inventory schema: 1.0.0
Corpus version: 1.0.0
Customer or production data: prohibited
```

## Purpose

This constitution defines the source-level controls for AuraGateway's frozen synthetic Nimbus Relay API corpus before retrieval implementation and tuning begin.

It prevents the corpus from drifting toward easy, repetitive, current-only documentation that would fail to test stale-source handling, conflict resolution, metadata filtering, near-duplicate displacement, incomplete guidance, or version-sensitive procedure selection.

## Workload boundary

The corpus represents a fictional developer platform called Nimbus Relay API.

Covered areas include:

- API keys and OAuth;
- pagination;
- rate limits and retries;
- error codes;
- webhooks;
- SDK setup;
- API versioning;
- idempotency;
- file uploads;
- events;
- incidents;
- permissions;
- sandbox limitations.

## Frozen source requirements

The corpus contains:

| Requirement | Frozen count |
|---|---:|
| Documents | 30 |
| Distinct intent categories | 35 |
| Deliberately stale documents | 5 |
| Deliberately conflicting documents | 6 |
| Incomplete-guidance documents | 4 |
| Near-duplicate documents | 4 |
| Version-sensitive procedure documents | 9 |

Only Markdown and JSON source documents are permitted.

## Required metadata

Every source declares:

```text
source_id
document_path
title
version
topic
api_area
status
updated_at
document_format
intent_categories
data_classification
is_stale
conflict_group_id
completeness
near_duplicate_group_id
version_sensitive_procedure
supersedes_source_id
contains_personal_data
contains_secrets
```

A matching metadata subset is embedded in every source file. The Pydantic boundary is the authoritative schema.

## Diagnostic design rules

### Stale sources

A stale source is marked `deprecated` or `superseded` in metadata and carries an explicit lifecycle warning in its content.

Stale sources remain retrieval test assets. They are not silently deleted because they are needed to evaluate stale-source selection and metadata filtering.

### Conflicting sources

Every conflict group contains at least two sources that disagree on a material operational fact:

- API-key lifetime;
- webhook retry window;
- idempotency retention.

The authoritative source is distinguishable through version, status, update metadata, supersession, and content evidence.

### Incomplete guidance

Incomplete documents contain an explicit `Known gap` section and omit one or more details necessary for safe task completion. They still contain enough relevant information to remain plausible retrieval candidates.

### Near duplicates

Near-duplicate groups contain substantial semantic overlap with a meaningful difference in SDK scope or document format:

- HTTP pagination versus SDK pagination;
- Markdown event catalogue versus JSON event catalogue.

### Version-sensitive procedures

Version-sensitive procedures produce a different safe answer when the selected API or document version changes.

## Privacy and safety

All corpus content is synthetic.

The corpus excludes:

- customer or employee data;
- usable access tokens or API keys;
- copied production logs;
- real email addresses or phone numbers;
- real incidents;
- vendor-confidential material;
- instructions that weaken repository or provider security controls.

Example credentials use environment-variable placeholders.

## Freeze controls

The freeze validator enforces:

- exact inventory-to-file-set parity;
- no missing or extra Markdown and JSON files;
- embedded metadata parity with the source inventory;
- valid UTF-8;
- valid JSON source structure;
- explicit stale lifecycle warnings;
- explicit known-gap sections for incomplete sources;
- forbidden secret-pattern rejection;
- deterministic per-document SHA-256 values;
- deterministic byte counts;
- inventory SHA-256;
- source-manifest SHA-256;
- typed freeze-record parity.

## Frozen artifacts

```text
data/corpus/source_inventory.json
data/corpus/source_manifest.json
data/corpus/corpus_freeze_record.json
data/corpus/documents/**
```

The source manifest records every document path, source ID, format, byte count, and SHA-256 hash.

Any content or metadata change requires a new corpus version, regenerated freeze evidence, retrieval reruns, and an updated execution-manifest reference.

## Evidence boundary

This corpus freeze proves:

- all 30 documents exist;
- every document matches its inventory metadata;
- diagnostic quotas are present;
- stale and incomplete sources expose their required warnings;
- documents contain no matched forbidden secret patterns;
- the authored source set is byte-hashed and reproducible;
- the corpus is ready for chunking implementation and development retrieval evaluation.

It does not prove:

- chunking quality;
- dense or sparse retrieval quality;
- held-out retrieval performance;
- retrieval-configuration freeze;
- Gate 1 completion.
