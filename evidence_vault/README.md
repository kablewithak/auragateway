# AuraGateway Evidence Vault

This directory is the repository-adjacent root for finalized public-safe benchmark evidence.

## Permitted public-safe content

- typed benchmark manifests;
- configuration fingerprints;
- metadata-only run results;
- failure and exclusion ledgers;
- sanitized trace samples;
- eligibility decisions;
- quality, feedback, telemetry, and statistical reports;
- artifact hash manifests;
- generated case-study tables.

## Prohibited content

- raw prompts or user messages;
- raw retrieved document text;
- raw provider payloads;
- raw model outputs;
- protected blinded-review exports;
- credentials, tokens, or secrets;
- direct personal identifiers;
- hidden reasoning.

Protected and transient artifacts belong under `.local/`, which must remain ignored by Git.

Finalized evidence bundles are append-only. Corrections create a new bundle with explicit supersession metadata; existing finalized evidence is not edited or deleted in place.
