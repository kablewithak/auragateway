---
source_id: NR-WEBHOOK-013
version: 3.0
status: current
updated_at: 2026-03-15T09:00:00Z
document_format: markdown
api_area: webhooks
is_stale: false
conflict_group_id: webhook-retry-window
completeness: complete
near_duplicate_group_id: null
version_sensitive_procedure: true
---

# Webhook delivery and retry schedule

> **Current guidance:** This v3 schedule replaces `NR-WEBHOOK-014`.

Nimbus Relay attempts delivery immediately and then retries failed deliveries over a 72-hour window.

## Retry schedule

Attempts occur at approximately 1 minute, 5 minutes, 30 minutes, 2 hours, 8 hours, 24 hours, 48 hours, and 72 hours after the initial failure. A `2xx` response marks the delivery complete. Redirects, timeouts, and other statuses are failures.

## Ordering and duplication

Delivery order is not guaranteed across different event objects. A single event can be delivered more than once. Consumers must verify the signature and deduplicate by `event_id`.

## Endpoint health

Nimbus Relay pauses an endpoint after twenty consecutive failed deliveries. Restoring the endpoint does not replay events older than the 72-hour retention window. Operators can request a replay only for events still retained.

## Conflict boundary

The legacy 48-hour schedule in `NR-WEBHOOK-014` is stale. Current troubleshooting must use this document for v3 endpoints.
