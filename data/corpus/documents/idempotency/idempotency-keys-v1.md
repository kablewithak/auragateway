---
source_id: NR-IDEM-021
version: 1.2
status: deprecated
updated_at: 2023-12-01T09:00:00Z
document_format: markdown
api_area: idempotency
is_stale: true
conflict_group_id: idempotency-retention
completeness: complete
near_duplicate_group_id: null
version_sensitive_procedure: false
---

# Legacy idempotency key retention

> **Lifecycle warning:** DEPRECATED and superseded by `NR-IDEM-020`. This document describes API v1.2.

Legacy Nimbus Relay retained idempotency records for 24 hours. Repeating the same key and request body during that period returned the original response. Reusing the key with a changed body returned a conflict.

Clients were advised to keep their own operation ledger after the 24-hour retention window.

## Do not use for API v2

Current API v2 retention is 48 hours. The current replay and ambiguous-response procedure is defined in `NR-IDEM-020`. This source is intentionally retained to test stale-source selection and version conflict handling.
