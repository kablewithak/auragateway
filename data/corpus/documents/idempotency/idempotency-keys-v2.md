---
source_id: NR-IDEM-020
version: 2.0
status: current
updated_at: 2026-04-05T09:00:00Z
document_format: markdown
api_area: idempotency
is_stale: false
conflict_group_id: idempotency-retention
completeness: complete
near_duplicate_group_id: null
version_sensitive_procedure: true
---

# Idempotency key retention and replay

> **Current guidance:** API v2 retains idempotency records for 48 hours. This document supersedes `NR-IDEM-021`.

Send `Idempotency-Key` on supported create and mutation endpoints. The key must be unique within the workspace and endpoint for one logical operation.

## Replay behaviour

When the same key and byte-equivalent request body are repeated within 48 hours, Nimbus Relay returns the original operation result. A changed request body returns `409 IDEMPOTENCY_BODY_MISMATCH` and does not execute a second operation.

## Ambiguous responses

If a network timeout occurs after dispatch, retry with the same key and identical body. Do not generate a new key until the original operation state is resolved.

## Expiry

After 48 hours, the record may be removed and the key can no longer prove replay safety. Clients requiring longer reconciliation must retain their own operation ledger.

## Conflict boundary

The 24-hour retention period in `NR-IDEM-021` applies only to legacy API v1.2 and is stale.
