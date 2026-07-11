# ADR-0010: Immutable Evidence Bundles and Comparison Eligibility

- **Status:** Accepted
- **Date:** 2026-07-12
- **Decision owners:** AuraGateway project maintainers
- **Applies from:** Phase 0
- **Supersedes:** None

## Context

AuraGateway's primary product is evidence, not a running gateway.

Benchmark reports are trustworthy only when a reviewer can identify the exact configuration, account for every scheduled run, verify artifact integrity, reproduce derived reports, and see when comparisons were blocked.

Mutable result folders, overwritten reports, deleted failures, and manual comparison selection would undermine the project even if the runtime code were correct.

## Decision

Every completed benchmark execution will produce an append-only evidence bundle with typed manifests and SHA-256 artifact hashes.

Completed bundles are never edited in place.

Corrections or reruns produce new bundles that reference the prior bundle through explicit supersession metadata.

Comparison eligibility is machine-decided before comparative metrics or claims are generated.

## Bundle identity

Every bundle has:

- `evidence_bundle_id`;
- `run_group_id`;
- benchmark constitution version and hash;
- benchmark manifest hash;
- configuration fingerprint;
- Git commit hash;
- creation timestamp;
- schema version;
- bundle status;
- optional superseded bundle ID;
- optional supersession reason.

Bundle identifiers must be unique and must not expose PII.

## Required bundle files

A complete benchmark bundle contains:

```text
benchmark_manifest.json
configuration_fingerprint.json
environment_manifest.json
run_results.jsonl
failures.jsonl
exclusions.jsonl
reruns.jsonl
comparison_eligibility.json
comparison.csv
benchmark_report.md
sanitized_trace_samples.jsonl
artifact_hashes.json
bundle_manifest.json
```

A functional-only dry run may omit comparison outputs only when the bundle manifest explicitly declares the reduced bundle type.

Unknown or absent evidence is represented explicitly. Missing values are not fabricated.

## Run accountability

Every scheduled run appears in exactly one terminal status:

- completed;
- completed with validation failure;
- provider error;
- budget exhausted;
- excluded by predeclared rule;
- invalidated by configuration mismatch;
- aborted by safety control.

Retries and reruns do not erase the original record.

## Append-only rule

After bundle finalization:

- existing files are not modified;
- existing files are not deleted;
- artifact hashes are not regenerated in place;
- reports are not silently corrected;
- failures and exclusions remain visible.

A correction creates a new bundle.

The new bundle records:

- prior bundle ID;
- correction reason;
- affected artifacts;
- whether benchmark runs were repeated;
- which prior claims are superseded.

## Hash manifest

`artifact_hashes.json` contains, for every retained artifact:

- relative path;
- byte count;
- SHA-256 hash;
- artifact type;
- schema version where applicable.

The bundle manifest itself records the hash-manifest hash.

Secrets, raw prompts, raw provider payloads, protected review exports, and local credentials must never enter the bundle.

## Configuration fingerprint

The comparison fingerprint includes at minimum:

- corpus manifest hash;
- retrieval configuration hash;
- prompt template ID and version;
- static context-pack ID and version;
- tool-contract version;
- output-schema version;
- evaluation manifest hashes;
- quality rubric version;
- blinded-adjudication protocol version;
- negative-control manifest hash;
- fault-injection fixture hash;
- telemetry-sufficiency rules version;
- route-policy version;
- runtime condition implementation version;
- benchmark runner version;
- statistical reporting configuration version;
- comparison-eligibility contract version;
- pricing schedule version when applicable;
- provider/model alias;
- provider adapter version;
- Python version;
- dependency lock hash;
- Git commit hash.

## Comparison eligibility

Comparison is permitted only when all controlled fingerprint fields required for the contrast match.

The typed decision includes:

- `eligible`;
- compared run IDs;
- mismatched fields;
- invalidated metrics;
- invalidated claims;
- required reruns;
- decision reason codes;
- comparison-contract version.

Human-authored report text may not override an ineligible decision.

## Eligibility outcomes

### Eligible

Comparative metrics and conditional claims may be generated, subject to telemetry sufficiency and quality gates.

### Ineligible

The bundle may still report individual-condition facts, failures, and diagnostic findings.

It may not report comparative improvement or regression for invalidated metrics.

### Partially eligible

Partial eligibility is allowed only when the comparison contract explicitly identifies independent metric families.

For example, a pricing-schedule mismatch may invalidate cost comparison while leaving task-quality comparison eligible, provided no other controlled field changed.

Partial eligibility must be machine-readable and conservative.

## Report generation

Reports are derived from finalized machine-readable artifacts.

The report generator must:

- refuse unsupported comparative sections;
- identify failed, excluded, retried, and invalidated runs;
- distinguish provider-observed, locally inferred, and unavailable evidence;
- evaluate quality non-inferiority before accepting savings;
- include bundle and configuration identifiers;
- include artifact verification instructions.

Manual editing of generated result claims is prohibited. Narrative case-study documents may summarize the generated report but must cite the bundle ID.

## Reproducibility

The project must support deterministic commands equivalent to:

```powershell
python -m apps.benchmark_runner validate-config
python -m apps.benchmark_runner run --manifest .\data\evals\benchmark_manifest.json
python -m apps.benchmark_runner report --run-id <run-id>
python -m apps.benchmark_runner verify-bundle --bundle <bundle-path>
```

Exact command names may change, but validation, execution, reporting, and verification remain separate explicit operations.

## Storage posture

Initial storage is local and repository-adjacent:

- source-controlled schemas and manifests live in the repository;
- completed public-safe evidence may live in `evidence_vault/`;
- transient and protected artifacts live under `.local/`;
- cloud object storage is not required for the 200-hour project.

A later storage adapter may be added without weakening bundle immutability or comparison rules.

## Consequences

### Positive

- Benchmark evidence can be audited independently of prose.
- Failed and inconvenient results remain visible.
- Comparison drift becomes machine-detectable.
- Corrections retain history.
- Reports can be reproduced and verified.

### Negative

- Evidence consumes more local storage.
- Corrections require new bundles rather than simple edits.
- Schema and version discipline become mandatory.
- Comparison may be blocked even when runs appear superficially similar.

## Required verification

Implementation must prove:

- finalized bundles reject mutation;
- every scheduled run is accounted for;
- artifact hashes detect changed bytes;
- supersession preserves the prior bundle;
- fingerprint mismatches block affected comparisons;
- report generation honours eligibility and telemetry sufficiency;
- forbidden private artifacts cannot enter the public bundle.
