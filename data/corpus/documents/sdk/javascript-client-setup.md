---
source_id: NR-SDK-017
version: 4.1
status: current
updated_at: 2026-03-20T10:00:00Z
document_format: markdown
api_area: sdk
is_stale: false
conflict_group_id: null
completeness: complete
near_duplicate_group_id: null
version_sensitive_procedure: false
---

# JavaScript SDK client setup

Install the Nimbus Relay SDK and create a configured client from environment-provided credentials.

```text
npm install @nimbus-relay/sdk@4.1
```

```javascript
import { NimbusClient } from "@nimbus-relay/sdk";

const client = new NimbusClient({
  apiKey: process.env.NIMBUS_API_KEY,
  apiVersion: "2026-04",
  timeoutMs: 30000,
});
```

## Runtime requirements

Use Node.js 20 or later. Sandbox and production credentials are not interchangeable. Keep retries bounded and avoid retrying ambiguous non-idempotent writes.

## Errors

The SDK exposes `error.code`, `error.status`, `error.traceId`, and `error.retryable`. Branch on the stable code and endpoint semantics, not message text.

## Secret handling

Do not bundle credentials into browser applications. The JavaScript SDK setup documented here is for trusted server-side runtimes only. Browser clients must call an authenticated application backend.
