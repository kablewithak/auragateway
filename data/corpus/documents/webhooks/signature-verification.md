---
source_id: NR-WEBHOOK-015
version: 3.0
status: current
updated_at: 2026-03-16T09:00:00Z
document_format: markdown
api_area: webhooks
is_stale: false
conflict_group_id: null
completeness: complete
near_duplicate_group_id: null
version_sensitive_procedure: false
---

# Webhook signature verification

Nimbus Relay signs the exact UTF-8 request body with HMAC-SHA256.

## Headers

Each delivery includes `Nimbus-Signature` and `Nimbus-Timestamp`. The signature header contains the hexadecimal digest over:

```text
${timestamp}.${raw_request_body}
```

Use the endpoint signing secret from the secret manager. Compute the digest over the untouched raw bytes and compare with a constant-time equality function.

## Replay protection

Reject a timestamp more than five minutes from the receiving server clock. Record the event ID after successful verification and ignore duplicate deliveries already processed.

## Common failures

Parsing and reserializing JSON before verification changes whitespace and key order, producing `SIGNATURE_MISMATCH`. Using the API key instead of the endpoint signing secret also fails. Clock drift produces `TIMESTAMP_OUTSIDE_WINDOW`.

Do not log the signing secret, raw body, or computed secret material. Safe logs may retain the event ID, timestamp age, verification result, and trace ID.
