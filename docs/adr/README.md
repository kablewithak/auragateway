# AuraGateway Architecture Decision Records

This directory contains the architectural decisions governing AuraGateway.

The ADR set is part of the experiment-control surface. Decisions affecting controlled constants, causal contrasts, telemetry meaning, evaluation policy, privacy, or evidence handling must be versioned and reviewed before benchmark execution.

## Status vocabulary

- **Proposed:** drafted but not accepted
- **Accepted:** governs implementation
- **Superseded:** replaced by a later ADR
- **Deprecated:** retained for history but no longer recommended

## ADR index

| ADR | Title | Status |
|---|---|---|
| [ADR-0001](ADR-0001-scope-and-non-goals.md) | AuraGateway Scope and Non-Goals | Accepted |
| [ADR-0002](ADR-0002-benchmark-constitution-and-causal-contrasts.md) | Benchmark Constitution and Causal Contrasts | Accepted |
| [ADR-0009](ADR-0009-privacy-safe-observability.md) | Privacy-Safe Observability | Accepted |
| [ADR-0010](ADR-0010-immutable-evidence-bundles-and-comparison-eligibility.md) | Immutable Evidence Bundles and Comparison Eligibility | Accepted |

## Planned ADRs

The PRD requires the following additional decisions before the corresponding implementation boundary is considered stable:

| ADR | Planned title |
|---|---|
| ADR-0003 | Canonical Context Serialization |
| ADR-0004 | Prefix Fingerprinting |
| ADR-0005 | Provider Telemetry Semantics |
| ADR-0006 | Cache-Affinity Route Policy |
| ADR-0007 | Quality Evaluation and Blinded Adjudication |
| ADR-0008 | EFC Evidence Contract |

Planned ADRs are not yet accepted decisions.
