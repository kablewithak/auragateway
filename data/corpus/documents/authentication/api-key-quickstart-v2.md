---
source_id: NR-AUTH-001
version: 2.0
status: current
updated_at: 2026-01-15T09:00:00Z
document_format: markdown
api_area: authentication
is_stale: false
conflict_group_id: auth-token-lifetime
completeness: complete
near_duplicate_group_id: null
version_sensitive_procedure: true
---

# API key authentication quickstart

> **Current guidance:** Use this procedure for Nimbus Relay API v2. API keys expire after 24 hours and must be rotated rather than extended.

## Create and store the key

Create a key in the developer console for the smallest required environment and permission set. The console displays the secret value once. Store it in the `NIMBUS_API_KEY` environment variable or an approved secret manager. Do not place the value in source code, request logs, screenshots, tickets, or benchmark traces.

## Send an authenticated request

Use the bearer scheme on every HTTPS request:

```http
Authorization: Bearer ${NIMBUS_API_KEY}
X-Nimbus-Api-Version: 2026-04
```

A missing header returns `401 AUTH_HEADER_MISSING`. An expired key returns `401 KEY_EXPIRED`. A valid key without permission returns `403 PERMISSION_DENIED`; rotating the key does not fix a permission error.

## Rotation procedure

Create the replacement key, update the application secret, verify one read-only request, and then revoke the old key. During a controlled rotation, both keys may overlap for at most ten minutes. Nimbus Relay does not extend the 24-hour lifetime of an existing key.

## Diagnostic boundary

This document supersedes `NR-AUTH-002`. Any guidance claiming seven-day keys is stale and must not be used for v2 requests.
