---
source_id: NR-ERROR-011
version: 5.2
status: current
updated_at: 2026-03-10T09:00:00Z
document_format: markdown
api_area: error_codes
is_stale: false
conflict_group_id: null
completeness: complete
near_duplicate_group_id: null
version_sensitive_procedure: false
---

# API error-code reference

Nimbus Relay errors include an HTTP status, stable machine code, safe message, and trace identifier.

## Authentication and permission

- `401 AUTH_HEADER_MISSING`: no bearer token was supplied.
- `401 KEY_EXPIRED`: the API key lifetime ended.
- `403 PERMISSION_DENIED`: the authenticated principal lacks the required action.
- `403 WORKSPACE_MISMATCH`: the resource belongs to another workspace.

## Request correctness

- `400 CURSOR_CONTEXT_MISMATCH`: a cursor was reused with changed context.
- `409 RESOURCE_STATE_CONFLICT`: the request conflicts with the current resource state.
- `422 FIELD_VALIDATION_FAILED`: the request shape is understood but one or more fields are invalid.

## Transient service failures

- `429 RATE_LIMITED`: wait for `Retry-After`.
- `503 SERVICE_UNAVAILABLE`: retry only under the bounded retry policy.
- `504 UPSTREAM_TIMEOUT`: response completion may be ambiguous for writes.

Do not infer retryability from the HTTP status alone. Use the stable code, endpoint semantics, idempotency support, and response-state classification.
