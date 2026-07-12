# AuraGateway Canonical Prefix Design

## Purpose

This design defines the deterministic static-prefix compiler used by AuraGateway Condition B and Condition C.

It converts a frozen, typed static compiler specification and the ordered static-anchor registry into one provider-neutral canonical UTF-8 payload. The payload is fingerprinted with HMAC-SHA256 using key material supplied only through local environment settings.

The design does not perform provider calls, model execution, routing, or cache measurement.

## Inputs

The compiler consumes:

- `data/context/static_anchor_registry.json`
- `data/context/compiler_spec.json`
- every artifact referenced by the static-anchor registry
- a local HMAC key and non-secret key ID from environment settings

The compiler specification freezes:

- template ID and version
- serialization version
- tool-contract version
- ordered static text segments
- ordered tool contracts and ordered tool fields
- ordered output-schema fields and schema version
- approved reusable context-pack ID, version, and content
- static-anchor registry path and SHA-256

## Canonicalization Rules

Canonical static serialization uses:

- UTF-8 encoding
- CRLF and CR normalization to LF
- trailing horizontal whitespace removal
- one terminal newline for normalized text
- deterministic JSON key ordering
- compact JSON separators
- explicit array order for segments, tools, fields, and anchors
- explicit serialization version
- validated contiguous order values
- hash verification for every registered static artifact

JSON key order is not semantically significant. Equivalent objects with different input key order serialize to identical canonical bytes.

Tool order, schema order, segment order, and anchor order are semantically significant and are validated before serialization.

## Static and Volatile Isolation

Static content may contain:

- system behaviour policy
- task procedure
- citation rules
- immutable few-shot examples
- output schema
- stable tool contracts
- approved context pack
- version and artifact references

The raw compiler input is scanned before typed validation. Volatile or secret-bearing keys are blocked, including:

- timestamps
- request IDs
- session IDs
- direct user identifiers
- retrieval evidence
- conversation history
- runtime token counts
- provider responses or payloads
- temporary flags
- random values
- secrets and API keys

Volatile append logs are never included in canonical static serialization.

## Prefix Fingerprint

The static prefix fingerprint is:

```text
HMAC-SHA256(local_environment_key, canonical_static_provider_bytes)
```

The key is never written to the repository, report, manifest, trace, or error envelope.

Safe retained evidence includes:

- non-secret key ID
- prefix fingerprint
- canonical byte count
- canonical SHA-256
- serialization version
- template ID and version
- tool-contract fingerprint
- output-schema fingerprint
- context-pack fingerprint
- static-anchor registry SHA-256

Raw static content is not copied into public traces or fingerprint reports.

## Five-Turn Stability Audit

The Gate 3 fixture contains five controlled turns. Each turn appends additional typed volatile items while preserving the same static compiler specification and anchor registry.

For every turn, the verifier records only:

- turn index
- volatile-log SHA-256
- volatile item count
- static prefix fingerprint
- whether the fingerprint matches the baseline

All five turns must match the baseline fingerprint.

## Mutation Calibration

Seven cases are frozen:

1. timestamp insertion
2. tool-order change
3. output-schema version change
4. JSON key-order change
5. one-byte few-shot example change
6. volatile user-content change
7. retrieval-order change

Expected behaviour:

- timestamp insertion is blocked before typed compilation
- tool-order change changes the fingerprint
- output-schema version change changes the fingerprint
- JSON key-order change is canonically equivalent
- one-byte static example change changes the fingerprint
- volatile user-content change does not change the static fingerprint
- retrieval-order change does not change the static fingerprint

The verifier rejects both missed mutations and false-positive mutations.

## Privacy and Security Boundary

This is a synthetic local benchmark fixture.

Controls:

- HMAC key loaded from environment settings
- minimum 32-byte HMAC key
- no key material in artifacts or logs
- no PII or secrets in static or volatile fixtures
- no raw static or volatile content in public evidence
- safe typed CLI errors only
- immutable hash-bound evidence artifacts

The committed validation fingerprint uses a named synthetic fixture key. It is not a production secret and does not establish a production key-management posture.

## Maintainability

The provider-neutral canonical payload is isolated from future provider adapters.

A provider adapter may transform the typed canonical payload into provider-specific request objects later, but any material provider serialization change must produce a new serialization version and new fingerprint evidence.
