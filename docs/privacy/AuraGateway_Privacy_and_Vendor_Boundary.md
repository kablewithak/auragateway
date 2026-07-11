# AuraGateway Privacy and Vendor Boundary

## Status

```text
Version: 0.1.0
State: Phase 0 design control
Customer data: prohibited
Legal status: engineering control document, not legal advice
```

## Purpose

This document defines what AuraGateway may process, transmit, retain, log, review, and publish during the 200-hour project.

It operationalizes the privacy and vendor-boundary requirements from the PRD and ADR-0009.

## Data posture

AuraGateway uses synthetic project data only.

Permitted source data:

- synthetic Nimbus Relay API documentation;
- synthetic benchmark user messages;
- synthetic retrieval cases;
- synthetic provider fixtures;
- generated identifiers without personal meaning;
- versioned pricing and provider documentation metadata.

Prohibited source data:

- customer documents;
- production conversations;
- production logs;
- employee or applicant records;
- financial-account data;
- healthcare data;
- credentials;
- secrets;
- direct personal identifiers.

## Data classes

| Class | Examples | Repository | Runtime memory | Normal logs | Public evidence |
|---|---|---:|---:|---:|---:|
| Public project metadata | versions, aliases, hashes | Yes | Yes | Yes | Yes |
| Synthetic corpus source | Nimbus Relay documents | Yes | Yes | No raw text | Source IDs only |
| Synthetic user content | benchmark messages | Yes, controlled assets | Yes | No | No |
| Model output | benchmark response | No public source path | Yes | No | Opaque review export only |
| Provider payload | SDK response object | No | Adapter only | No | No |
| Protected review content | blinded output package | No, `.local/` only | Yes | No | No |
| Credentials and secrets | API keys, tokens, HMAC key | No | Environment only | No | No |
| PII | email, phone, identity data | Prohibited | Prohibited | Prohibited | Prohibited |

## Processing purposes

Data may be processed only to:

- construct the fixed benchmark;
- execute retrieval and runtime conditions;
- validate structured outputs and citations;
- evaluate route and feedback behaviour;
- calculate permitted metrics;
- reproduce reports;
- diagnose typed failures;
- perform blinded quality review.

Data may not be reused for:

- model training;
- behavioural profiling;
- advertising;
- unrelated experimentation;
- cross-project identity correlation.

## Provider transmission boundary

Before a live provider is enabled, the adapter record must document:

- provider;
- exact model alias;
- provider adapter version;
- prompt and content categories transmitted;
- whether content leaves South Africa;
- documentation date checked;
- cache and retention assumptions;
- telemetry fields expected;
- pricing source date;
- deletion or zero-retention controls where available;
- known unknowns.

No claim of POPIA, GDPR, or GLBA compliance may be made from this record alone.

## Minimization rules

Transmit only the content required for the benchmark turn.

Do not transmit:

- local file paths;
- Git metadata;
- operator identity;
- credentials;
- unrelated corpus content;
- hidden labels revealing benchmark condition;
- protected review identifiers;
- raw trace history when bounded state is sufficient.

## Observability rules

Normal logs and public traces use typed metadata only.

Allowed:

- IDs;
- source references;
- fingerprints;
- versions;
- durations;
- token counts;
- route reasons;
- validation states;
- failure labels;
- safe error envelopes.

Forbidden:

- raw prompt;
- raw user message;
- raw retrieved text;
- raw output;
- raw provider response;
- secret;
- PII;
- unbounded metadata.

## Retention schedule

| Artifact | Default retention |
|---|---|
| Raw provider response object | Request lifetime only |
| Temporary provider debugging fixture | Until fixture sanitization is verified |
| Normal structured logs | Bounded local rotation |
| Protected blinded-review export | Through adjudication and final report verification |
| Synthetic benchmark source assets | Project lifetime |
| Final sanitized evidence bundle | Project lifetime, append-only |
| Superseded sanitized evidence bundle | Project lifetime with supersession link |
| Secrets | Never persisted |

Exact log rotation and protected-review deletion periods must be pinned before live benchmark execution.

## Deletion controls

Deletion must:

- target a declared artifact class;
- preserve a metadata-only deletion record where required;
- avoid logging deleted content;
- verify removal from temporary directories;
- avoid mutating finalized public evidence bundles.

A finalized bundle is superseded, not edited.

## Access posture

Local access follows least privilege:

- provider credentials available only to the live adapter process;
- HMAC key available only to fingerprinting code;
- protected review exports accessible only during review;
- public evidence excludes protected artifacts;
- development, test fixtures, and live credentials remain separated.

## Environment separation

Minimum environments:

- deterministic test and fixture mode;
- local live-provider smoke mode;
- controlled benchmark execution mode.

A live credential must not be required for unit tests or report reproduction from an existing bundle.

## Incident boundary

The project must treat the following as blocking failures:

- credential committed or logged;
- raw provider payload persisted;
- forbidden trace field accepted;
- customer or production data introduced;
- protected review artifact copied into a public bundle;
- direct identifier included in a session or cache namespace;
- comparison report generated from contaminated evidence.

Response priorities:

1. stop affected execution;
2. preserve safe metadata evidence;
3. revoke exposed credentials;
4. isolate contaminated artifacts;
5. document affected runs and claims;
6. create a superseding clean bundle where possible.

## Future customer-data work

Customer-data testing is outside the current project.

A future scope would require, at minimum:

- explicit customer authorization;
- data-processing and vendor-boundary review;
- data classification;
- regional-transfer assessment;
- access-control design;
- retention and deletion agreement;
- incident process;
- isolated environment;
- separate evidence and claim label.

The current synthetic-data harness must not be relabelled as customer-data ready.
