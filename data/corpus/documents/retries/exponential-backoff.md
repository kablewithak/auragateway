---
source_id: NR-RETRY-009
version: 3.0
status: current
updated_at: 2026-03-05T09:00:00Z
document_format: markdown
api_area: retries
is_stale: false
conflict_group_id: null
completeness: complete
near_duplicate_group_id: null
version_sensitive_procedure: true
---

# Exponential backoff and retry policy

Nimbus Relay clients may retry only failures classified as transient and safe.

## Retryable conditions

Retry `408`, `429`, `502`, `503`, and `504` when the response state is a definite failure or no response was received. Honour `Retry-After` when present. For other transient failures, use delays of 1, 2, 4, and 8 seconds with bounded jitter outside measured benchmark execution.

## Non-retryable conditions

Do not retry authentication, permission, validation, conflict, or unsupported-operation errors without changing the request or obtaining new evidence. Do not automatically retry after an ambiguous timeout when the server may have completed a non-idempotent write.

## Idempotency

Writes that support idempotency keys may be retried with the same key and identical request body. Changing either value creates a new operation. For endpoints without idempotency support, escalate ambiguous completion rather than risking a duplicate.

## Limits

Application clients should cap retries at four attempts. AuraGateway benchmark execution uses its separately frozen provider-request policy and does not inherit this application-client limit.
