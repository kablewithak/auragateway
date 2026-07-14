# ADR: Build a Static Hugging Face Publication Package from Sanitized Evidence

## Status

Accepted for the local publication-candidate slice.

## Context

AuraGateway has two terminal live-provider lineages and no eligible A/B/C cache benchmark.

```text
Groq:
  two successful raw-wire responses
  required cached-token field absent

OpenRouter / Hy3:
  one cold attempt
  HTTP 401 before successful inference
  no generation metadata or cache telemetry
```

The repository already contains sanitized closeouts and a terminal provider evidence review. The next
phase is public proof packaging, not another experiment.

A publication layer can easily distort this result by adding live inference, implying that missing
telemetry is zero, presenting HTTP 401 as a model result, or copying protected local artifacts into a
public repository.

## Decision

Build a deterministic local adapter that produces two standalone candidates:

```text
release/hugging-face/dataset/auragateway-provider-evidence
release/hugging-face/space/auragateway-provider-evidence
```

The Dataset candidate contains sanitized JSONL records, a claim matrix, methodology, evidence
boundaries, attribution, a provisional license notice, and a candidate manifest.

The Space candidate is a static HTML/CSS/JavaScript case study. It reads only a generated local
`evidence.js` file and performs browser-local filtering. It does not call a provider or retain user
input.

The builder validates the exact terminal source state before generating either candidate. It rejects
comparison eligibility, live inference, credentials, customer data, raw provider payloads, or drifted
terminal evidence.

Remote publication remains a separate authorization gate.

## Why static HTML

The evidence is precomputed and read-only. Static HTML minimizes the operational boundary:

```text
no Python runtime on Hugging Face
no API key
no model dependency
no remote inference
no server-side state
no user-input retention
```

## License decision

The local candidate uses Hugging Face metadata value `license: other`. This slice does not choose a
public reuse license on the repository owner's behalf. Remote publication is blocked until a specific
license is selected and reconciled across Dataset and Space artifacts.

## Consequences

### Positive

- The public package is reproducible from committed sanitized evidence.
- Negative and inconclusive outcomes remain visible.
- The Space cannot silently become a live benchmark.
- Candidate files are hash-bound.
- Secret and protected-path scans are machine enforced.

### Costs

- A separate controlled publication step is still required.
- The repository owner must choose a publication license.
- Any source evidence change requires rebuilding and recommitting both candidates.

## Non-claims

This decision does not establish:

```text
provider cache performance
cost or latency savings
successful Hy3 inference
A/B/C benchmark completion
remote Hugging Face publication
production readiness
```
