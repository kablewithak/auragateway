# ADR-0007: Quality Evaluation and Blinded Adjudication

- **Status:** Accepted
- **Date:** 2026-07-12
- **Decision version:** 1.3.0
- **Decision owners:** AuraGateway project maintainers
- **Applies from:** Phase 5
- **Supersedes:** None

## Context

AuraGateway cannot interpret runtime improvement as useful unless task quality remains inside the frozen non-inferiority boundary. Free-form model judgment is too weak as the first line of evaluation because schema validity, source scope, citation identity, terminal decisions, and explicitly declared claim support can be checked deterministically.

The diagnostic episode set already freezes required and forbidden sources, terminal decisions, decision-specific requirements, and failure labels. Gate 6 needs an executable scoring boundary that consumes those assets without changing them or exposing raw candidate content in retained score reports.

Residual questions such as whether wording resolves the technical issue or whether an explanation is persuasive still require condition-blind rubric review. Those questions must not be disguised as deterministic checks.

## Decision

AuraGateway evaluates task quality in three ordered layers.

### Layer 1: deterministic quality scoring

The deterministic scorer checks:

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

Deterministic results contain hashes, IDs, check outcomes, and failure labels. They do not retain raw response text, raw prompts, raw documents, or hidden reasoning.

### Layer 2: blinded rubric review

Residual qualitative judgment uses opaque review IDs. Reviewers must not receive condition, provider, model, route, cost, latency, cache telemetry, or run-order fields.

The frozen review workflow requires:

- one primary review assignment for every functional episode;
- an independent secondary review for the deterministic 25 percent sample;
- five double-reviewed episodes under the frozen 18-episode benchmark;
- a versioned seven-criterion rubric;
- criterion scores from one to four;
- a total passing threshold of 21;
- no criterion score below two for a passing verdict;
- explicit failure labels;
- rationale and evidence-note digests rather than hidden reasoning;
- material-disagreement detection;
- independent adjudication when material disagreement is present;
- prohibition of adjudication when no material disagreement exists.

The residual-quality criteria are task correctness, evidence grounding, source use, terminal decision, completeness, clarity, and safety.

### Layer 3: A/B/C quality non-inferiority gate

Measured condition comparison is interpreted only after deterministic scoring and protected review controls are complete.

The comparison gate requires exactly one aggregate for each of conditions A, B, and C. Condition A is the frozen baseline. Conditions B and C are evaluated against it.

A comparison is eligible only when:

- all conditions use the same retrieval-configuration fingerprint;
- all conditions use the same frozen episode-manifest digest;
- every condition meets the minimum sample count;
- answer and citation-support denominators are non-zero.

Eligible conditions must satisfy:

- structured-output validity of at least 95 percent;
- no citation-support-rate regression against condition A;
- no unsupported-answer-rate increase against condition A;
- task success no more than five percentage points below condition A.

The 95 percent structured-output threshold and the five-percentage-point task-success margin are inclusive. Configuration mismatch produces `ineligible`, weak evidence produces `insufficient_sample`, and neither state is reported as an ordinary quality failure.

The first implementation of this layer is a synthetic dry run. It validates the decision boundary but does not execute providers or authorize measured claims.

## Opaque assignment policy

Review assignments are deterministic and provider-neutral. Opaque review IDs do not encode episode, provider, model, condition, route, cost, latency, cache state, or run order.

The double-review sample is selected by ranking SHA-256 digests of the frozen sampling seed and episode IDs. Input episode ordering must not affect the assignment manifest.

## Protected review export

The pre-blinding source envelope may contain experimental fields, but the reviewer export contains only approved review-visible evidence. Condition, provider, model, route, cost, latency, cache telemetry, and run order are stripped before export.

Protected review exports may contain synthetic or private review content. Public reports retain only hashes, IDs, counts, bounded outcomes, and failure codes.

## Material disagreement and adjudication

A primary and secondary review materially disagree when verdicts differ, any criterion score differs by at least two points, or failure-label sets differ.

Primary and secondary reviewers must be independent. Material disagreement requires an independent adjudication record. Adjudication is rejected when the reviews do not materially disagree.

## Claim-support registry

Natural-language entailment is not treated as deterministic. Answer claims are normalized and hashed. A frozen human-authored registry maps each accepted semantic claim digest to supporting and contradicting source IDs.

A claim absent from the registry is unsupported for deterministic purposes. This does not prove that every possible paraphrase or fact has been semantically evaluated.

## Source-age rule

A stale source is not automatically invalid. A frozen episode may require a stale or superseded source to explain a conflict. The deterministic failure is an unscoped stale source used outside the episode's required or optional source scope.

## Consequences

### Positive

- Machine-checkable failures are separated from residual qualitative judgment.
- Frozen episode expectations become executable quality gates.
- Experimental fields are stripped before review.
- Review coverage and adjudication completeness are machine checked.
- Comparison eligibility is separated from comparison outcome.
- Retrieval or episode drift cannot produce a passing comparison.
- Insufficient evidence cannot be misreported as non-inferiority.
- Later measured A/B/C comparisons reuse the exact same thresholds and result taxonomy.

### Negative

- Human-authored claim registries require controlled maintenance.
- Deterministic checks cannot establish whether arbitrary prose is clear, complete, or persuasive.
- Rubric interpretation can vary across reviewers.
- Aggregate-rate gates can hide episode-level failure clusters unless trace review is retained.
- A synthetic dry run is necessary but not sufficient for Gate 6 completion.

## Required verification

The quality non-inferiority dry run must prove that:

- the exact 95 percent structured-output boundary passes;
- the exact five-percentage-point task-success margin passes;
- structured validity below threshold fails;
- citation-support regression fails;
- unsupported-answer-rate increase fails;
- task-success loss beyond the margin fails;
- multiple regressions retain stable failure codes;
- retrieval fingerprint drift is ineligible;
- episode-manifest drift is ineligible;
- insufficient sample count is explicit;
- missing rate denominators are explicit;
- condition input ordering does not change the result;
- proportional count scaling does not change rates or status;
- fixture, report, manifest, and upstream hashes reproduce.

## Gate status

This decision version establishes deterministic quality scoring, blinded-review preparation, protected synthetic review execution, and a synthetic A/B/C quality non-inferiority dry run.

Gate 6 remains open until protected reviews are completed on measured trajectories and an eligible A/B/C held-out comparison passes the frozen quality boundary.

## Claim boundary

The current Gate 6 layers prove typed deterministic scoring, blinded workflow preparation, protected synthetic execution, and quality-gate decision behavior on frozen synthetic evidence.

They do not prove completed human review, reviewer reliability on measured trajectories, measured A/B/C task-quality non-inferiority, benchmark readiness, latency improvement, cost reduction, deployment safety, or production readiness.
