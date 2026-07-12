# Nimbus Relay Retrieval Metadata Remediation Design

## Status

```text
Design version: 1.0.0
Scope: development remediation after held-out v1
Frozen corpus changed: no
Held-out v1 changed: no
Gate 1 status: blocked pending held-out v2
```

## Problem

Held-out v1 showed that lexical and local dense ranking were not sufficient to distinguish sources
that shared topic vocabulary but described different application contracts.

The observed failures were:

- OAuth client credentials versus refresh-token troubleshooting;
- Python versus JavaScript SDK guidance;
- raw HTTP pagination versus SDK pagination;
- human-readable versus machine-readable representations.

Increasing score weights or lowering Gate 1 thresholds would hide the boundary defect. The correct
intervention is deterministic source applicability metadata applied before ranking.

## Non-destructive design

The frozen corpus, generated chunks, development v1, and held-out v1 remain byte-for-byte unchanged.

The remediation adds a separate retrieval metadata overlay:

```text
data/retrieval/remediation-v1/source_metadata.json
```

The overlay is bound to the frozen corpus-manifest SHA-256 and must cover exactly the same 30 source
IDs as each evaluated chunking candidate.

## Typed discriminators

Every source receives:

- `language`;
- `interface_kind`;
- `oauth_grant`;
- `representation`.

Supported values are intentionally small.

### Language

```text
language_agnostic
python
javascript
```

Language-specific sources must use the SDK interface.

### Interface kind

```text
general
raw_http
sdk
```

### OAuth grant

```text
not_applicable
client_credentials
refresh_token
```

Grant-specific sources must use the raw HTTP interface.

### Representation

```text
human_guide
machine_reference
```

## Query contract

`RetrievalFilter` now supports an optional typed metadata constraint.

The constraint is absent for all v1 queries, preserving v1 serialization and deterministic evidence.
When present, exact-match filters run before BM25 scoring or dense-vector similarity.

If a query declares metadata constraints and a source has no metadata record, the source is ineligible.
Unknown metadata never behaves as a wildcard.

## Remediated candidates

Two finalist configurations are evaluated:

```text
bm25-fixed-window-remediated-v2
dense-hashed-tfidf-section-aware-remediated-v2
```

Both retain their prior algorithm and chunking configuration. The intervention is limited to:

- metadata-registry binding;
- pre-ranking applicability filtering;
- development-v2 query constraints.

This preserves a clear before/after causal interpretation.

## Development-v2 changes

Development v2 reuses the 24 accepted query texts and failure hypotheses from development v1.

Seven cases gain typed applicability filters:

```text
dev-ret-009  OAuth refresh-token semantics
dev-ret-012  raw HTTP pagination
dev-ret-013  Python SDK pagination
dev-ret-014  human-readable event catalogue
dev-ret-015  machine-readable event catalogue
dev-ret-023  Python SDK setup
dev-ret-024  JavaScript SDK setup
```

Grade-one alternative representations are retained as near-duplicate negative controls rather than
counted as relevant sources in development v2.

## Failure handling

The remediation verifier rejects:

- metadata registry and corpus-manifest hash mismatch;
- missing or extra source metadata;
- duplicate source metadata IDs;
- invalid language/interface combinations;
- invalid OAuth-grant/interface combinations;
- modified candidate manifests;
- modified case results;
- modified scorecards;
- modified comparison reports.

## Gate boundary

Development remediation cannot close Gate 1.

A new held-out v2 asset must be authored and frozen without editing held-out v1. Gate 1 remains blocked
until the remediated finalists pass the frozen held-out policy.
