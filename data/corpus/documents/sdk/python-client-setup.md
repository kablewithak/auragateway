---
source_id: NR-SDK-016
version: 4.1
status: current
updated_at: 2026-03-20T09:00:00Z
document_format: markdown
api_area: sdk
is_stale: false
conflict_group_id: null
completeness: complete
near_duplicate_group_id: null
version_sensitive_procedure: false
---

# Python SDK client setup

Install the Nimbus Relay Python SDK in an isolated environment and create one client per configuration boundary.

```text
pip install nimbus-relay==4.1.*
```

```python
import os
from nimbus_relay import NimbusClient

client = NimbusClient(
    api_key=os.environ["NIMBUS_API_KEY"],
    api_version="2026-04",
    timeout_seconds=30,
)
```

## Configuration

Use the sandbox base URL only for sandbox credentials. Configure bounded timeouts and application-level retry policy explicitly. The SDK does not log request bodies or authentication headers unless unsafe debug hooks are added by the application.

## Errors

The SDK maps stable API codes to typed exceptions such as `AuthenticationError`, `PermissionError`, `ValidationError`, and `RateLimitError`. Inspect the machine code and trace ID rather than matching message text.

## Lifecycle

Close the client when the process or worker ends. Reuse the configured client within that lifecycle rather than creating a new connection pool for each request.
