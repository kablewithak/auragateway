# ADR-0009: Privacy-Safe Observability

- **Status:** Accepted
- **Date:** 2026-07-12
- **Decision owners:** AuraGateway project maintainers
- **Applies from:** Phase 0
- **Supersedes:** None

## Context

AuraGateway needs enough runtime evidence to reproduce benchmark results, diagnose failures, enforce comparison eligibility, and review route and feedback behaviour.

The naive observability approach would retain complete prompts, user messages, retrieved documents, model outputs, and raw provider responses. That would make debugging convenient but would create unnecessary privacy, secret-leakage, retention, repository, and vendor-boundary risk.

AuraGateway uses synthetic data, but the harness must still establish the controls expected of a production-shaped reliability system. Synthetic content does not justify unrestricted logging.

## Decision

AuraGateway will use metadata-safe observability.

Public traces, normal JSON logs, comparison tables, and report artifacts may contain only bounded typed metadata required to explain system behaviour.

Raw content is excluded by default and must not cross the trace-writer boundary.

## Allowed trace fields

The trace contract may include:

- `trace_id`;
- `run_id`;
- `comparison_pair_id`;
- `episode_id`;
- `condition_id`;
- `replication_id`;
- `turn_index`;
- provider and model aliases;
- route reason;
- template and contract versions;
- configuration fingerprint;
- prefix fingerprint;
- cache-evidence summary;
- usage and timing metrics;
- retrieval source IDs and chunk IDs;
- retrieval scores and metric summaries;
- terminal decision;
- validation result;
- failure labels;
- feedback-evidence summary;
- safe typed error code;
- artifact references and hashes.

Metadata containers must be bounded and schema-defined. Unrestricted dictionaries are prohibited at trace boundaries.

## Forbidden trace content

The trace writer must reject:

- raw prompts;
- raw system instructions;
- raw user messages;
- raw conversation history;
- raw retrieved document text;
- raw model outputs;
- hidden reasoning;
- raw provider payloads;
- API keys;
- access tokens;
- secrets;
- email addresses;
- phone numbers;
- full names used as identifiers;
- unredacted direct user identifiers;
- arbitrary unbounded metadata.

A forbidden field is a `PRIVACY_VIOLATION`, not a warning.

## Protected local review artifacts

Some task-quality review may require model-output content.

Where content is required for blinded review:

- it is stored only in a protected local review export;
- it uses opaque review IDs;
- it excludes credentials and direct personal data;
- it is excluded from Git;
- it is excluded from public evidence bundles;
- it has an explicit retention and deletion rule;
- it is never included in normal application logs.

Protected review artifacts remain separate from public sanitized traces.

## Fingerprints and identifiers

Static content is represented in traces by HMAC-SHA256 fingerprints, versions, and segment identifiers.

Requirements:

- the HMAC key is loaded from local environment settings;
- the HMAC key is never committed;
- raw static content cannot be recovered from the trace;
- direct user identifiers are replaced with salted or HMAC-based local identifiers;
- identifiers do not permit cross-project tracking.

## Provider boundary

Provider adapters are the only modules allowed to inspect raw provider SDK objects or payloads.

Before a request crosses the provider boundary, the run record must declare:

- provider and model alias;
- data categories transmitted;
- whether prompts leave local execution;
- documentation date checked;
- telemetry fields expected;
- retention or cache assumptions being used;
- known uncertainty.

Raw provider responses are converted immediately into typed response and telemetry contracts. Raw payloads are not persisted.

## Logging and error handling

Logs use structured JSON and safe error envelopes.

Logs may contain:

- error codes;
- retryability;
- timeout values;
- response-state classification;
- bounded safe messages;
- trace and run IDs.

Logs may not contain raw request or response bodies.

Blanket exception handling is prohibited. Error taxonomy must preserve enough meaning to determine whether retry, reroute, exclusion, or escalation is permitted.

## Retention and deletion

The project must define retention by artifact class.

Minimum rules:

- temporary local provider-response memory: request lifetime only;
- normal runtime logs: bounded local rotation;
- protected review exports: deleted after adjudication and final report verification unless a documented review need remains;
- completed sanitized evidence bundles: retained as append-only project evidence;
- superseded evidence bundles: retained with supersession metadata;
- secrets and credentials: never stored in artifacts.

Deletion actions affecting protected review artifacts must be auditable without logging deleted content.

## Repository controls

The repository must ignore:

- `.env`;
- `.env.*`, except an approved `.env.example`;
- `.local/`;
- protected review exports;
- provider credentials;
- raw runtime payload captures.

A repository scan must be part of the release gate before evidence publication.

## Regulatory alignment

These are engineering controls aligned with data-minimization, purpose-limitation, retention, deletion, least-privilege, and auditability principles associated with POPIA, GDPR, and GLBA-style expectations.

They are not legal compliance claims.

## Consequences

### Positive

- Public traces remain safe to inspect and share.
- Provider payload semantics remain isolated.
- Accidental secret and content persistence becomes a testable failure.
- Evidence remains useful through versions, identifiers, hashes, timings, and failure labels.
- Future customer-data work would begin from a safer harness boundary.

### Negative

- Some debugging becomes less convenient.
- Protected review exports require a separate controlled workflow.
- Trace design must be explicit rather than accepting arbitrary dictionaries.
- Raw provider discrepancies must be diagnosed inside adapter tests and fixtures.

## Required verification

Implementation must include deterministic tests proving:

- forbidden content is rejected;
- unknown metadata fields are rejected or explicitly versioned;
- safe typed traces serialize;
- HMAC fingerprints remain stable for stable content;
- provider payloads do not escape adapters;
- protected review exports are excluded from Git and public evidence bundles.
