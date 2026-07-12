# ADR-0007: Quality Evaluation and Blinded Adjudication

- **Status:** Accepted
- **Date:** 2026-07-12
- **Decision owners:** AuraGateway project maintainers
- **Applies from:** Phase 5
- **Supersedes:** None

## Context

AuraGateway cannot interpret runtime improvement as useful unless task quality remains inside the frozen non-inferiority boundary. Free-form model judgment is too weak as the first line of evaluation because schema validity, source scope, citation identity, terminal decisions, and explicitly declared claim support can be checked deterministically.

The diagnostic episode set already freezes required and forbidden sources, terminal decisions, decision-specific requirements, and failure labels. Gate 6 needs an executable scoring boundary that consumes those assets without changing them or exposing raw candidate content in retained score reports.

Residual questions such as whether wording resolves the technical issue or whether an explanation is persuasive still require condition-blind rubric review. Those questions must not be disguised as deterministic checks.

## Decision

AuraGateway will evaluate task quality in two ordered layers.

### Layer 1: deterministic quality scoring

The deterministic scorer will check:

- structured terminal-output validity;
- retrieval-configuration fingerprint equality;
- expected terminal decision and reason code;
- retrieved source-ID validity;
- required-source presence;
- forbidden-source absence;
- exclusion of stale sources outside the episode's declared scope;
- citation-ID validity;
- proof that cited sources were retrieved;
- required citation presence;
- required and forbidden semantic claim digests;
- claim-to-source support against a frozen human-authored registry;
- decision-specific clarification, escalation, and refusal fields.

Deterministic results will contain hashes, IDs, check outcomes, and failure labels. They will not retain raw response text, raw prompts, raw documents, or hidden reasoning.

### Layer 2: blinded rubric review

Residual qualitative judgment will use opaque review IDs. Reviewers must not receive condition, provider, model, route, cost, latency, cache telemetry, or run-order fields. All functional trajectories receive primary review, and the frozen 25 percent sample receives independent double review. Material disagreements require adjudication.

The rubric and review workflow will be implemented in a later Gate 6 slice. This ADR accepts the architecture now; it does not claim that blinded adjudication has been executed.

## Claim-support registry

Natural-language entailment is not treated as deterministic. Answer claims are normalized and hashed. A frozen, human-authored registry maps each accepted semantic claim digest to supporting and contradicting source IDs. The scorer verifies declared claim evidence against that registry.

A claim absent from the registry is unsupported for deterministic purposes. This does not prove that every possible paraphrase or fact has been semantically evaluated.

## Source-age rule

A stale source is not automatically invalid. A frozen episode may require a stale or superseded source to explain a conflict. The deterministic failure is therefore an **unscoped stale source**: a stale source used outside the episode's required or optional source scope.

## Consequences

### Positive

- Machine-checkable failures are separated from residual qualitative judgment.
- Frozen episode expectations become executable quality gates.
- Citation and source-use regressions receive stable labels.
- Retrieval configuration drift blocks a passing result.
- Raw candidate content stays outside retained scorecards.
- Later A/B/C quality comparisons can use identical scorer versions.

### Negative

- Human-authored claim registries require controlled maintenance.
- Deterministic checks cannot establish whether arbitrary prose is clear, complete, or persuasive.
- Passing deterministic checks is necessary but not sufficient for Gate 6 completion.
- Rubric versioning and adjudication execution remain additional work.

## Required verification

The deterministic slice must prove that:

- a grounded answer passes;
- malformed structured output fails;
- required clarification is not silently answered;
- incomplete clarification fails;
- justified escalation and refusal pass;
- mismatched escalation reasons fail;
- forbidden and unscoped stale sources fail;
- unknown citations fail;
- unregistered claim digests fail;
- forbidden claims fail;
- retrieval fingerprint drift fails;
- required-source absence fails;
- source-order changes do not change results;
- retained scorecards exclude raw candidate output;
- frozen fixture and report hashes reproduce.

## Claim boundary

This ADR and its first implementation slice prove deterministic scoring behavior on fixed synthetic fixtures. They do not prove semantic answer quality, citation entailment beyond the frozen claim registry, rubric reliability, reviewer agreement, task-quality non-inferiority, benchmark readiness, latency improvement, cost reduction, deployment safety, or production readiness.
