---
source_id: NR-OAUTH-003
version: 3.1
status: current
updated_at: 2026-02-03T09:00:00Z
document_format: markdown
api_area: oauth
is_stale: false
conflict_group_id: null
completeness: complete
near_duplicate_group_id: null
version_sensitive_procedure: true
---

# OAuth client credentials flow

Use the client-credentials grant for server-to-server workloads that do not act on behalf of a human user.

## Token request

Send a form-encoded `POST` request to `/oauth/token` with `grant_type=client_credentials`, the registered client identifier, and the client secret supplied through the approved secret boundary. Request only the scopes needed by the workload.

The response contains an access token, its scope set, and `expires_in=900`. Access tokens therefore expire after fifteen minutes. Nimbus Relay does not issue refresh tokens for the client-credentials grant. Request a new access token when the current token expires.

## Validation rules

A client identifier registered for the sandbox cannot request production scopes. An unknown scope returns `400 invalid_scope`. Incorrect credentials return `401 invalid_client`. Repeating the same invalid request will not produce new information and should not trigger unbounded retries.

## Safe handling

Do not log the request body, client secret, or access token. Logs may retain the provider-neutral error code, requested scope names, trace identifier, and retryability decision.
