# ADR-0007: Quality Evaluation and Blinded Adjudication

- **Status:** Accepted
- **Date:** 2026-07-12
- **Decision version:** 1.2.0
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

The seven residual-quality criteria are:

1. task correctness;
2. evidence grounding;
3. source use;
4. terminal decision;
5. completeness;
6. clarity;
7. safety.

### Opaque assignment policy

Review assignments are deterministic and provider-neutral.

For each episode and role, AuraGateway derives:

- an opaque review ID;
- an assignment-key SHA-256 digest;
- a primary or secondary role.

The double-review sample is selected by ranking SHA-256 digests of the frozen sampling seed and episode IDs. Input episode ordering must not affect the resulting assignment manifest.

Opaque review IDs do not encode the episode ID, provider, model, condition, route, cost, latency, cache state, or run order.

### Protected review export

The pre-blinding source envelope may contain experimental fields, but the reviewer export contains only:

- opaque review ID;
- episode ID;
- synthetic conversation;
- terminal decision output;
- citation source IDs;
- deterministic validation results.

The following fields are stripped before export:

- condition ID;
- provider;
- model;
- route;
- cost;
- latency;
- cache telemetry;
- run order.

Protected review exports may contain synthetic or private review content. Public reports retain only hashes, IDs, counts, bounded outcomes, and failure codes.

### Material disagreement

A primary and secondary review materially disagree when at least one of the following is true:

- the pass/fail verdict differs;
- any criterion score differs by at least two points;
- the failure-label sets differ.

Primary and secondary reviewer identities must be different. Reviewer identities are retained only as SHA-256 digests in the protected workflow record.

### Independent adjudication

Material disagreement requires an adjudication record that:

- references the disputed primary and secondary review IDs;
- uses an adjudicator identity distinct from both reviewers;
- records final criterion scores;
- records final failure labels;
- records a final verdict consistent with the frozen rubric;
- retains only a rationale digest in public evidence.

Adjudication is rejected when the two reviews do not materially disagree.

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
- Raw candidate content stays outside retained deterministic scorecards.
- Experimental fields are stripped before review.
- Every functional episode receives a primary review slot.
- The double-review sample is deterministic and reproducible.
- Material disagreements receive stable reasons.
- Adjudicator independence is machine checked.
- Later A/B/C quality comparisons can use identical scorer and rubric versions.

### Negative

- Human-authored claim registries require controlled maintenance.
- Deterministic checks cannot establish whether arbitrary prose is clear, complete, or persuasive.
- Blinded-review preparation does not itself execute human review.
- Protected exports require stricter storage and access controls than public reports.
- Rubric interpretation can still vary across reviewers.
- Passing preparation fixtures is necessary but not sufficient for Gate 6 completion.

## Required verification

The deterministic scorer slice must prove that:

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

The blinded-review preparation slice must prove that:

- all 18 functional episodes receive primary assignments;
- exactly five episodes receive secondary assignments;
- the frozen sample reproduces from seed and episode IDs;
- assignment results do not depend on input episode ordering;
- opaque review IDs do not expose episode identities;
- prohibited experimental fields are absent from reviewer exports;
- changes to hidden fields do not change reviewer exports;
- primary and secondary reviewers must be independent;
- verdict, score-delta, and failure-label disagreements are detected;
- material disagreements require adjudication;
- adjudicators must be independent;
- unnecessary adjudication is rejected;
- fixture, assignment, report, and manifest hashes reproduce.

## Gate status

This decision version establishes deterministic quality scoring, blinded-review preparation, and protected synthetic review execution.

Gate 6 remains open until protected reviews are completed on measured trajectories and A/B/C held-out quality non-inferiority evidence is produced.

## Protected review execution

The prepared blinded workflow is followed by a protected execution boundary that validates complete assignment coverage before producing aggregate quality evidence.

The execution layer must:

- accept exactly one review for every frozen primary and secondary assignment;
- reject missing, duplicate, or unassigned review submissions;
- validate every review against its assignment and the frozen rubric;
- require independent primary and secondary reviewers;
- detect material disagreement using the accepted verdict, score-delta, and failure-label rules;
- require exactly one independent adjudication for every material disagreement;
- prohibit adjudication when no material disagreement exists;
- calculate reviewer-agreement metrics from the frozen double-review sample;
- produce metadata-only episode outcomes and held-out aggregates;
- exclude raw conversations, candidate outputs, reviewer notes, and rationales from public reports.

When double reviews do not materially disagree, the primary review remains the final episode outcome. When a material disagreement is adjudicated, the adjudication becomes the final outcome. This rule is deterministic and versioned.

The first execution evidence is synthetic fixture execution. It validates workflow behavior and aggregate calculations but does not claim that human review or provider-condition comparison has occurred.

## Claim boundary

The deterministic scorer, blinded preparation layer, and protected synthetic execution layer prove typed coverage enforcement, assignment matching, reviewer independence, material-disagreement handling, adjudication completeness, agreement metrics, and metadata-only held-out aggregation on frozen synthetic evidence.

They do not prove completed human review, reviewer reliability on real trajectories, A/B/C task-quality non-inferiority, benchmark readiness, latency improvement, cost reduction, deployment safety, or production readiness.
