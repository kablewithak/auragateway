# Nimbus Relay Synthetic Corpus Constitution

## Document control

```text
Version: 1.0.0
Status: Accepted for Phase 1 corpus authoring
Benchmark Constitution dependency: 1.0.0
Corpus inventory schema: 1.0.0
Customer or production data: prohibited
```

## Purpose

This constitution defines the source-level controls for AuraGateway's synthetic Nimbus Relay API corpus before any document text or retrieval implementation is created.

It prevents corpus authoring from drifting toward easy, repetitive, current-only documentation that would fail to test stale-source handling, conflict resolution, metadata filtering, near-duplicate displacement, incomplete guidance, or version-sensitive procedure selection.

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

## Minimum source requirements

The authored corpus must contain at least:

| Requirement | Minimum |
|---|---:|
| Documents | 30 |
| Distinct intent categories | 10 |
| Deliberately stale documents | 5 |
| Deliberately conflicting documents | 5 |
| Incomplete-guidance documents | 4 |
| Near-duplicate documents | 4 |
| Version-sensitive procedure documents | 6 |

Only Markdown and JSON source documents are permitted.

## Required metadata

Every source must declare:

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

The Pydantic boundary is the authoritative schema.

## Diagnostic design rules

### Stale sources

A stale source must be marked `deprecated` or `superseded`.

Stale sources remain retrievable test assets. They are not silently deleted because they are needed to evaluate stale-source selection and metadata filtering.

### Conflicting sources

Every conflict group contains at least two sources that disagree on a material operational fact, such as token lifetime, retry timing, or idempotency retention.

The authoritative source must be distinguishable through version, status, and update metadata rather than trivial wording such as "this document is wrong."

### Incomplete guidance

Incomplete documents omit one or more details necessary for safe task completion. They must still contain enough relevant information to be plausible retrieval candidates.

### Near duplicates

Near-duplicate groups contain at least two documents with substantial semantic overlap but meaningful differences in scope, format, SDK, or authority.

### Version-sensitive procedures

Version-sensitive procedures must produce a different safe answer when the selected API or document version changes.

## Privacy and safety

All corpus content is synthetic.

The corpus must not contain:

- real customer or employee data;
- real access tokens or API keys;
- copied production logs;
- real email addresses or phone numbers;
- real incidents;
- vendor-confidential material;
- instructions that weaken repository or provider security controls.

Example credentials must use unmistakably non-secret placeholders.

## Authoring acceptance rules

A document is accepted only when:

- its source ID and path match the inventory;
- its metadata validates;
- it serves at least one declared intent;
- its diagnostic role is real rather than cosmetic;
- its content does not contradict its declared lifecycle metadata accidentally;
- it contains no personal data or secrets;
- it is grounded in the fictional Nimbus Relay domain;
- it does not reveal hidden benchmark labels in user-facing prose.

A document is rejected when it is:

- trivial;
- ambiguous without diagnostic purpose;
- a duplicate without a declared near-duplicate role;
- impossible to distinguish from its conflict counterpart through metadata and evidence;
- unrelated to the benchmark workload;
- dependent on real customer data;
- written mainly to make retrieval metrics easier.

## Freeze sequence

1. Validate the planned inventory.
2. Author all 30 documents.
3. Verify file existence and metadata parity.
4. Hash every source file.
5. Generate the corpus manifest.
6. Run privacy and secret scanning.
7. Freeze the authored corpus before retrieval tuning begins.

The current inventory is not the final corpus manifest because the source documents do not yet exist.

## Evidence boundary

This slice proves:

- the planned inventory is typed;
- source identities and paths are unique;
- required diagnostic quotas are present;
- conflict and near-duplicate groups are structurally valid;
- PII and secret flags are rejected;
- both Markdown and JSON formats are represented.

It does not prove:

- that the 30 documents have been authored;
- retrieval readiness;
- held-out retrieval quality;
- corpus hash freeze;
- Gate 1 completion.
