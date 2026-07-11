---
source_id: NR-VERS-018
version: 2026-04
status: current
updated_at: 2026-04-01T09:00:00Z
document_format: markdown
api_area: versioning
is_stale: false
conflict_group_id: null
completeness: complete
near_duplicate_group_id: null
version_sensitive_procedure: true
---

# API version migration procedure

Nimbus Relay uses the `X-Nimbus-Api-Version` request header. The current version is `2026-04`.

## Migration sequence

1. Inventory endpoints and SDK calls used by the application.
2. Read the deprecated endpoint register in `NR-VERS-019`.
3. Run contract tests against the sandbox with the target version header.
4. Update fields, event types, and pagination assumptions.
5. Deploy behind a controlled configuration flag.
6. Compare validation failures and unsupported responses.
7. Remove the previous version only after rollback evidence is retained.

## Compatibility boundary

A missing version header uses the workspace default and is not acceptable for reproducible clients. Cursors, webhook payload shapes, and some error codes are version-scoped.

## Rollback

Rollback restores the previous explicit version header and compatible client contract. It must not mix cursors, idempotency keys, or cached response assumptions across versions.
