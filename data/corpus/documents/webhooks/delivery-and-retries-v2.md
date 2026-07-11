---
source_id: NR-WEBHOOK-014
version: 2.4
status: superseded
updated_at: 2024-01-15T09:00:00Z
document_format: markdown
api_area: webhooks
is_stale: true
conflict_group_id: webhook-retry-window
completeness: complete
near_duplicate_group_id: null
version_sensitive_procedure: true
---

# Legacy webhook delivery and retry schedule

> **Lifecycle warning:** SUPERSEDED by `NR-WEBHOOK-013`. This document is intentionally stale and describes webhook API v2.4.

Legacy endpoints retried failed deliveries for 48 hours. Attempts occurred after 2 minutes, 10 minutes, 1 hour, 6 hours, 24 hours, and 48 hours.

An endpoint was paused after ten consecutive failures. Operators could request replay for events retained inside the 48-hour window.

## Legacy delivery rules

A `2xx` response completed delivery. Redirects and timeouts were failures. Event ordering was not guaranteed, and consumers were expected to deduplicate by event identifier.

## Do not apply to v3

The current v3 system uses a 72-hour retry window and a different pause threshold. Those rules are defined in `NR-WEBHOOK-013`. This source remains to create a deliberate version conflict for retrieval evaluation.
