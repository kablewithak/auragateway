---
source_id: NR-PAGE-006
version: 2.2
status: current
updated_at: 2026-02-13T09:00:00Z
document_format: markdown
api_area: pagination
is_stale: false
conflict_group_id: null
completeness: complete
near_duplicate_group_id: pagination-guides
version_sensitive_procedure: false
---

# Cursor pagination SDK guide

The Nimbus Relay SDKs expose the same opaque cursor contract as the HTTP API.

## Python

Create a page iterator with a limit from 1 to 100. The iterator forwards each `next_cursor` without decoding it.

```python
pages = client.events.pages(limit=50)
for page in pages:
    process(page.items)
```

## JavaScript

Use the asynchronous page iterator:

```javascript
for await (const page of client.events.pages({ limit: 50 })) {
  process(page.items);
}
```

## Cursor scope

A cursor belongs to one endpoint, workspace, filter set, sort order, and API version. Changing any of those values invalidates it. Cursors expire after ten minutes, after which the SDK raises `CursorExpiredError` and the traversal must restart.

## Duplicate handling

The SDK does not guarantee snapshot isolation while new records are created. Consumers should deduplicate by stable resource ID when a traversal overlaps concurrent writes.

## Related source

`NR-PAGE-005` documents the raw HTTP form. This document is intentionally similar, but queries about SDK exceptions and iterators should prefer this source.
