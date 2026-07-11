---
source_id: NR-SANDBOX-029
version: 1.9
status: current
updated_at: 2026-04-25T09:00:00Z
document_format: markdown
api_area: sandbox
is_stale: false
conflict_group_id: null
completeness: incomplete
near_duplicate_group_id: null
version_sensitive_procedure: false
---

# Sandbox environment limitations

The Nimbus Relay sandbox is isolated from production and uses synthetic resources.

## Supported behaviour

The sandbox supports authentication, standard CRUD operations, cursor pagination, deterministic error fixtures, and most webhook configuration endpoints. Sandbox credentials cannot access production resources.

## Differences from production

- lower rate limits;
- generated delivery latency;
- no real payment or external network side effects;
- synthetic incident states;
- file contents discarded after validation;
- reduced retention for test resources.

## Safe use

Use explicit sandbox credentials and base URL. Do not copy production secrets or customer records into the sandbox.

## Known gap

This document intentionally does not state whether every production webhook event type can be emitted on demand. When an integration requires a specific event simulation, query the sandbox capability endpoint or escalate rather than assuming support.
