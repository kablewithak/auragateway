---
source_id: NR-EVENT-024
version: 3.5
status: current
updated_at: 2026-04-15T09:00:00Z
document_format: markdown
api_area: events
is_stale: false
conflict_group_id: null
completeness: complete
near_duplicate_group_id: event-catalogues
version_sensitive_procedure: false
---

# Event type catalogue

Nimbus Relay publishes versioned event names. Consumers should subscribe only to event types they handle.

## Resource events

- `resource.created`: a new resource became visible.
- `resource.updated`: material fields changed.
- `resource.deleted`: the resource was deleted.

## Delivery events

- `delivery.succeeded`: a queued delivery completed.
- `delivery.failed`: delivery reached a terminal failure.
- `delivery.retrying`: another delivery attempt is scheduled.

## Security events

- `credential.rotated`: an API credential was replaced.
- `permission.changed`: a role or grant changed.

Event payloads include `event_id`, `event_type`, `created_at`, `api_version`, and a resource reference. Payloads are not guaranteed to contain the full current resource state; retrieve the resource when a workflow requires current data.

`NR-EVENT-025` contains the same catalogue in machine-readable JSON. This near-duplicate pair tests format-aware retrieval.
