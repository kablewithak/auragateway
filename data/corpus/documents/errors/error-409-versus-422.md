---
source_id: NR-ERROR-012
version: 5.2
status: current
updated_at: 2026-03-11T09:00:00Z
document_format: markdown
api_area: error_codes
is_stale: false
conflict_group_id: null
completeness: complete
near_duplicate_group_id: null
version_sensitive_procedure: false
---

# Distinguishing error 409 from 422

`409` and `422` both reject a request, but they describe different failure boundaries.

## `409 RESOURCE_STATE_CONFLICT`

Use `409` when the request is valid in isolation but conflicts with current server state. Examples include publishing an already-published release, reusing an idempotency key with a different body, or updating a resource with an outdated version token.

Resolution requires new state evidence: fetch the resource, compare the current version, and decide whether to retry with an updated precondition or stop.

## `422 FIELD_VALIDATION_FAILED`

Use `422` when the server understands the request shape but one or more field values violate declared constraints. Examples include an unsupported event type, a part size above the endpoint limit, or a missing conditional field.

Resolution requires changing the request fields. Fetching the resource state will not normally help.

## Retry rule

Neither code should be retried unchanged. A `409` may become retryable after state reconciliation. A `422` may be retried only after correcting the invalid field set.
