---
source_id: NR-RATE-008
version: 2.0
status: deprecated
updated_at: 2023-11-20T09:00:00Z
document_format: markdown
api_area: rate_limits
is_stale: true
conflict_group_id: null
completeness: complete
near_duplicate_group_id: null
version_sensitive_procedure: false
---

# Legacy rate-limit policy

> **Lifecycle warning:** DEPRECATED. This document is intentionally stale and describes the retired API v2 quota model.

Nimbus Relay previously applied a daily workspace quota of 25,000 requests and returned only `X-Daily-Limit` and `X-Daily-Remaining`. The counter reset at midnight UTC.

Clients were advised to retry a `429` after sixty seconds. That fixed delay is no longer reliable because the current platform returns `Retry-After` and uses minute and burst limits.

## Historical exception

Large legacy integrations could receive an account-specific daily quota. Those exceptions were removed during the v4 rate-limit migration.

## Do not use for current calculations

Current production limits and headers are defined by `NR-RATE-007`. This legacy source remains in the corpus to test stale-source filtering and version-sensitive troubleshooting.
