---
source_id: NR-INCIDENT-026
version: 1.8
status: current
updated_at: 2026-04-20T09:00:00Z
document_format: markdown
api_area: incidents
is_stale: false
conflict_group_id: null
completeness: incomplete
near_duplicate_group_id: null
version_sensitive_procedure: false
---

# Incident status and escalation guide

Nimbus Relay exposes incident states through the status API.

## States

- `investigating`: impact is being confirmed.
- `identified`: the failure source is known.
- `monitoring`: a mitigation is active and metrics are being watched.
- `resolved`: service health returned to the declared threshold.

## Client response

For a confirmed active incident, stop aggressive retries, preserve trace identifiers, and follow the endpoint-specific backoff guidance. Continue local validation so client-side errors are not misclassified as platform incidents.

## Escalation evidence

An escalation should include workspace identifier hash, affected endpoint, first and latest failure timestamps, stable error codes, trace IDs, request volume, and whether the issue reproduces in the sandbox.

## Known gap

This source intentionally does not define named support contacts, contractual severity timers, or customer-specific escalation channels. The assistant must escalate when those details are required rather than inventing them.
