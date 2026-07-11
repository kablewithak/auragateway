---
source_id: NR-AUTH-002
version: 1.4
status: superseded
updated_at: 2024-02-10T09:00:00Z
document_format: markdown
api_area: authentication
is_stale: true
conflict_group_id: auth-token-lifetime
completeness: complete
near_duplicate_group_id: null
version_sensitive_procedure: true
---

# Legacy API key authentication quickstart

> **Lifecycle warning:** SUPERSEDED by `NR-AUTH-001`. This document describes API v1.4 and is intentionally retained as stale benchmark evidence.

## Legacy behaviour

API v1.4 issued bearer keys with a seven-day lifetime. Clients sent the key in the `Authorization` header and did not include an explicit API-version header.

```http
Authorization: Bearer ${LEGACY_NIMBUS_KEY}
```

The legacy console allowed a key to be extended once before expiry. That extension workflow was removed in API v2. Modern clients must create and rotate a replacement key instead.

## Common legacy errors

`401 TOKEN_INVALID` indicated a malformed or revoked key. `403 ACCOUNT_SCOPE` indicated that the key belonged to a workspace without access to the requested resource.

## Do not apply to current traffic

This procedure conflicts with current v2 authentication rules in `NR-AUTH-001`. In particular, the seven-day lifetime, extension action, and missing version header are not valid for current Nimbus Relay traffic.
