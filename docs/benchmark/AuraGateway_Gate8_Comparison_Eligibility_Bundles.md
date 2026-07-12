# AuraGateway Gate 8 Comparison Eligibility and Evidence Bundles

## Purpose

This slice converts ADR-0010 into executable provider-free controls.

The implementation answers two separate questions:

1. Is the evidence bundle structurally valid and complete?
2. Which metric families, if any, are eligible for A/B/C comparison?

A valid bundle is not automatically an eligible comparison. An ineligible comparison does not erase individual-condition evidence.

## Deterministic boundary

The Gate 8 evaluator validates:

- one terminal record for every scheduled run;
- matching run, condition, and episode identities;
- explicit retention of failures and exclusions;
- configuration fingerprint self-consistency;
- required bundle artifacts;
- public-artifact safety;
- artifact-hash-manifest integrity;
- finalized bundle-content integrity;
- append-only supersession references;
- metric-family eligibility under a frozen comparison contract.

## Metric families

The comparison contract evaluates four independent metric families:

- cost;
- latency;
- quality;
- feedback.

A mismatch invalidates a family unless that exact field is predeclared as an allowed causal difference for that family.

The fixed contract demonstrates conservative partial eligibility. A pricing-schedule mismatch invalidates cost comparison while leaving quality, latency, and feedback eligible. Retrieval drift invalidates every family.

## Run accountability

Every scheduled run must appear exactly once in one terminal state:

- completed;
- completed with validation failure;
- provider error;
- budget exhausted;
- excluded by predeclared rule;
- invalidated by configuration mismatch;
- aborted by safety control.

Omitting an inconvenient run is a bundle failure. A predeclared exclusion remains valid only when the excluded run record is retained with its rule identifier.

## Public evidence boundary

The evaluator rejects artifact paths indicating:

- raw prompts;
- raw provider payloads;
- protected review exports;
- secrets;
- credentials;
- environment files.

The fixed evidence contains only synthetic metadata, hashes, IDs, counts, statuses, and bounded reason codes.

## Fixed cases

The deterministic fixture set covers:

- fully eligible complete bundle;
- partially eligible pricing mismatch;
- fully ineligible retrieval mismatch;
- missing scheduled-run evidence;
- missing required artifact;
- forbidden private artifact;
- mutated finalized bundle digest;
- inconsistent configuration fingerprint digest;
- valid explicit exclusion retention;
- valid append-only supersession.

## Verification

Run:

```powershell
python -m auragateway.evidence.runner verify --repo-root .
```

The command rebuilds the report and manifest from the fixed fixture set and compares them with the persisted artifacts.

## Evidence maturity

Status: synthetic-data validated, provider-free, locally reproducible.

Gate 8 remains open until measured benchmark execution produces finalized evidence bundles and the complete comparison/report pipeline consumes them without hidden exclusions or manual claim overrides.
