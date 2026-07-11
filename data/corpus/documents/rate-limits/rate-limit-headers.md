---
source_id: NR-RATE-007
version: 4.0
status: current
updated_at: 2026-03-01T09:00:00Z
document_format: markdown
api_area: rate_limits
is_stale: false
conflict_group_id: null
completeness: complete
near_duplicate_group_id: null
version_sensitive_procedure: true
---

# Rate-limit headers and quotas

Nimbus Relay API v4 applies a workspace-level token bucket and an endpoint burst limit.

## Response headers

Every authenticated response may include:

- `X-RateLimit-Limit`: maximum requests in the current minute;
- `X-RateLimit-Remaining`: requests remaining before the minute resets;
- `X-RateLimit-Reset`: UTC epoch second for the reset;
- `Retry-After`: whole seconds to wait after a `429` response.

The standard production workspace allowance is 600 requests per minute, with a burst ceiling of 50 requests per second per endpoint. Sandbox workspaces use lower limits.

## Handling `429`

Stop sending requests to the affected endpoint, wait for `Retry-After`, and resume with bounded concurrency. Do not retry immediately in parallel. A `429` is safe to retry only after the server-provided delay.

## Capacity requests

Quota increases require evidence of sustained demand, bounded concurrency, and idempotent retry behaviour. The client cannot change limits through an API call.

## Stale-source warning

`NR-RATE-008` describes a retired daily quota and must not be used for current production calculations.
