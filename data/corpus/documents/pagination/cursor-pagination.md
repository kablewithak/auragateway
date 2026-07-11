---
source_id: NR-PAGE-005
version: 2.2
status: current
updated_at: 2026-02-12T09:00:00Z
document_format: markdown
api_area: pagination
is_stale: false
conflict_group_id: null
completeness: complete
near_duplicate_group_id: pagination-guides
version_sensitive_procedure: false
---

# Cursor pagination guide

Nimbus Relay list endpoints use opaque forward cursors.

## First page

Call the collection endpoint with `limit` between 1 and 100. Do not invent a cursor for the first request.

```http
GET /v2/events?limit=50
```

The response contains `items` and `next_cursor`. When `next_cursor` is `null`, the traversal is complete.

## Following pages

Pass the returned cursor unchanged in the next request:

```http
GET /v2/events?limit=50&cursor=${NEXT_CURSOR}
```

Cursors are scoped to the endpoint, filters, sort order, workspace, and API version that created them. Reusing a cursor after changing any of those values returns `400 CURSOR_CONTEXT_MISMATCH`.

## Consistency and recovery

A cursor remains valid for ten minutes. If it expires, restart from the first page. Do not parse, trim, decode, or persist cursor internals. Deduplicate results by resource ID if records can be created during traversal.

## Related source

`NR-PAGE-006` provides the equivalent Python and JavaScript SDK workflow. The two guides intentionally overlap to test near-duplicate retrieval without changing the underlying pagination rules.
