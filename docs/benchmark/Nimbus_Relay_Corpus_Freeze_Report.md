# Nimbus Relay Corpus Freeze Report

## Decision

```text
Corpus: Nimbus Relay synthetic documentation
Corpus version: 1.0.0
Freeze status: PASS
Freeze date: 2026-07-12
Document count: 30
Total document bytes: 38,092
Inventory SHA-256: 25b34bbb646952f0b9345d25a9a958fcab9ca33e88696c474a41621e7f90a3be
Source manifest SHA-256: c68212afd5381dec8bce49d0d5fee231a3b5589bf5460c0f72297e0c84422f55
```

## Frozen inventory profile

| Diagnostic class | Count |
|---|---:|
| Distinct intent categories | 35 |
| Stale sources | 5 |
| Sources in conflict groups | 6 |
| Incomplete-guidance sources | 4 |
| Near-duplicate sources | 4 |
| Version-sensitive procedures | 9 |

## Material conflict groups

| Conflict group | Current guidance | Retained stale guidance |
|---|---|---|
| `auth-token-lifetime` | API v2 keys expire after 24 hours | API v1.4 keys lasted seven days |
| `webhook-retry-window` | Webhook v3 retries for 72 hours | Webhook v2.4 retried for 48 hours |
| `idempotency-retention` | API v2 retains records for 48 hours | API v1.2 retained records for 24 hours |

## Near-duplicate groups

| Group | Deliberate distinction |
|---|---|
| `pagination-guides` | Raw HTTP pagination versus SDK iterators and exceptions |
| `event-catalogues` | Human-readable Markdown versus machine-readable JSON |

## Incomplete-guidance sources

The four incomplete documents expose explicit known gaps rather than hiding missing information:

- multipart upload limits;
- incident escalation contacts and service levels;
- custom-role restricted permissions;
- sandbox event-simulation capability.

These gaps require clarification, retrieval of a stronger source, or escalation. They must not be filled through model invention.

## Verification performed

The deterministic verifier confirmed:

- all inventory paths exist;
- no extra corpus documents exist;
- embedded document metadata matches the inventory;
- all JSON documents parse into typed outer contracts;
- stale sources contain lifecycle warnings;
- incomplete sources contain known-gap sections;
- no configured secret-like patterns are present;
- each document byte count and SHA-256 matches the source manifest;
- the inventory hash matches the source manifest;
- the source-manifest hash matches the freeze record.

## Evidence boundary

The result supports the maturity label:

```text
Synthetic corpus locally validated and hash-frozen
```

It does not establish retrieval readiness. Gate 1 remains open until chunking strategies, sparse and dense retrieval, development scorecards, retrieval selection, and held-out validation are complete.

## Next controlled change

Implement the two required chunking strategies behind typed, deterministic interfaces:

1. fixed token-window chunking;
2. section-aware chunking with bounded fallback splitting.

Neither strategy may alter or rewrite the frozen source documents.
