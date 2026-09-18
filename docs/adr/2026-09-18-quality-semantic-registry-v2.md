# ADR: Introduce a Versioned Quality Semantic Registry V2

**Date:** 2026-09-18
**Status:** Proposed for implementation
**Scope:** Post-Final-342 evaluator qualification

## Context

Final-342 preserved a frozen blinded-quality rubric, failure-label inventory,
independent human review workflow, independent human adjudication workflow,
and a Jev shadow-adjudication experiment.

The historical assets remain valid evidence of what was executed under the
v1 contract. They must not be rewritten after observing calibration results.

J7 calibration exposed two specification problems that prevent several
observed model-versus-human disagreements from being interpreted as clean
evaluator failures.

### Finding 1: criterion applicability ambiguity

The frozen v1 `evidence_grounding` criterion asks whether material statements
are grounded in visible evidence.

Ten observed cases produced the maximum disagreement:

- authoritative human score: 1
- Jev score: 4

All ten cases shared the same response shape:

- terminal decision: clarify
- zero citations
- one missing field
- no substantive final answer
- four distinct episode IDs
- two distinct reason codes

The v1 rubric does not explicitly define how evidence grounding applies when
the response makes no substantive conclusion but still performs a terminal
action, asserts missing information, or asks a clarification question.

This permits incompatible interpretations such as:

1. the response failed to ground its terminal action in available evidence; or
2. there are no material conclusions to test, so grounding is vacuously
   satisfied.

That ambiguity prevents the observed 1-to-4 disagreements from being treated
as clean evidence of model failure.

### Finding 2: failure-label ontology underspecification

The v1 Jev boundary supplies failure labels primarily as enum names.

The human adjudication workflow also exposes the failure-label inventory
without a single versioned operational-definition registry.

`CONTRADICTORY_STATE` is used across multiple related scenarios, including:

- retrieval-configuration fingerprint mismatch;
- unresolved conflict between current and superseded evidence;
- stale maintained state after later evidence should replace it;
- unresolved contradictory user corrections;
- state conflict that materially changes the final action.

These uses are related but cannot safely be inferred from the enum name alone.

The observed Jev-vs-human exact failure-label-set agreement therefore remains
valid historical measurement, but it must not be interpreted as pure evaluator
accuracy until both humans and model evaluators receive the same explicit
semantic contract.

## Decision

Introduce a new versioned semantic contract:

`auragateway-quality-semantic-registry-v2`

The v2 registry is a new benchmark contract. It does not modify, replace, or
retroactively reinterpret the frozen Final-342 v1 evidence.

The registry will provide one canonical semantic source for:

- human primary reviewers;
- human secondary reviewers;
- human adjudicators;
- model evaluators such as Jev;
- deterministic validators where the semantic concept applies;
- tests and qualification harnesses.

## Criterion semantic contract

The registry must define all seven existing rubric criteria exactly once:

- task_correctness
- evidence_grounding
- source_use
- terminal_decision
- completeness
- clarity
- safety

Each criterion definition must contain:

- criterion identifier;
- description;
- applicability rule;
- rule for non-substantive responses;
- score 1 anchor;
- score 2 anchor;
- score 3 anchor;
- score 4 anchor;
- boundary notes.

A score must never become favourable merely because the evaluated response
omits the behaviour the criterion is intended to assess.

In particular, evidence grounding must explicitly treat terminal actions,
missing-field assertions, clarification questions, recommendations, and other
decision-bearing response acts as material when evidence can change whether
those acts are justified.

## Failure-label semantic contract

The registry must define all 22 `EpisodeFailureLabel` values exactly once.

Each failure-label definition must contain:

- exact label identifier;
- operational definition;
- one or more inclusion rules;
- one or more exclusion rules;
- related labels;
- deterministic or benchmark source references when available;
- positive example;
- near-miss example.

The registry must distinguish related labels rather than relying on their names.

For example, a future definition of `CONTRADICTORY_STATE` must distinguish
material state inconsistency from:

- merely missing information;
- uncertainty without contradictory evidence;
- ordinary unsupported claims;
- stale-source selection where no conflicting maintained state exists.

The final operational wording will be derived from existing executable checks,
accepted episode semantics, and benchmark evidence before it is frozen.

## Shared-consumer invariant

Human and model evaluation surfaces must consume the same registry version.

It is prohibited to maintain:

- richer private definitions for humans;
- reduced enum-only definitions for model evaluators;
- prompt-only semantics not represented in the typed registry;
- evaluator-specific label meanings.

Any transformation into reviewer instructions or provider questions must be a
deterministic projection of the same registry object.

## Versioning and evidence

Final-342 remains immutable.

The following historical artifacts retain their original meaning:

- rubric v1;
- human primary reviews;
- human secondary reviews;
- authoritative adjudications;
- Jev v1 requests and responses;
- J7 calibration reports;
- hashes and receipts.

The v2 registry creates a new semantic evaluation boundary.

No v2 result may be presented as if it were produced under the v1 contract.

Any change to:

- criterion applicability;
- score anchors;
- failure-label semantics;
- inclusion or exclusion rules;
- examples used as normative evaluation guidance

requires a new registry version and invalidates affected downstream
comparisons.

## Qualification strategy

Final-342 may be used as a development and diagnostic population for studying
known specification failures.

It must not become the independent qualification population for v2 because its
human decisions and Jev outcomes have already been observed.

Qualification under v2 requires fresh data with:

- PASS and FAIL outcomes;
- criterion-score variation where naturally available;
- label-present and label-absent examples;
- ordinary agreement cases;
- difficult disagreement cases;
- near-miss failure-label cases;
- frozen human authority established before model reveal.

Threshold selection must occur on development data only.

Any deployment or automation threshold must then be tested on separate,
pre-specified held-out evidence.

## Alternatives considered

### Keep v1 and improve the Jev prompt only

Rejected.

This would train the model to reproduce ambiguities in the benchmark rather
than repairing the benchmark contract. It would also leave humans and models
with different semantic information.

### Add prose definitions only to the Jev prompt

Rejected.

This creates evaluator-specific semantics and makes the provider request the
hidden source of truth.

### Rewrite the Final-342 rubric and adjudications

Rejected.

Historical evidence has already been observed and hash-bound. Retroactive
changes would destroy comparability and evidence integrity.

### Introduce one typed, versioned semantic registry

Accepted.

This preserves historical evidence, creates one source of truth, makes semantic
changes inspectable, and supports independent future qualification.

## Consequences

### Positive

- evaluator disagreements become more interpretable;
- model and human reviewers receive equivalent semantics;
- taxonomy drift becomes detectable;
- future thresholds can be qualified against a stable contract;
- failure-label definitions become testable rather than implicit;
- benchmark evolution becomes explicit and versioned.

### Costs

- all 22 failure labels require careful semantic audit;
- historical v1 scores cannot simply be relabelled as v2 scores;
- new human-reviewed qualification evidence is required;
- future registry changes require deliberate versioning.

## Implementation gates

### J7H — architecture freeze

This ADR only.

No Jev calls.
No Final-342 mutation.
No threshold selection.

### J7I — typed registry contract

Implement Pydantic v2 contracts for:

- criterion semantic definitions;
- failure-label semantic definitions;
- source references;
- complete registry validation;
- canonical registry hashing.

Tests must reject:

- missing criteria;
- duplicate criteria;
- missing failure labels;
- duplicate failure labels;
- self-referential related labels;
- unknown semantic source shapes;
- empty inclusion/exclusion rules;
- semantic inventory drift.

No provider calls.

### J7J — semantic population and audit

Populate all seven criteria and 22 failure labels from existing repository
evidence.

Every definition must be traceable to executable logic, accepted benchmark
semantics, or an explicitly documented new normative decision.

Ambiguous labels must be resolved before freeze.

### J7K — shared projection

Create deterministic projections of the v2 registry for:

- human-review work items;
- Jev questions.

Prove byte-stable registry identity across both consumers.

### J7L — development evaluation

Use fresh development cases to compare the existing evaluator against the
repaired semantic contract.

Record baseline, intervention, failures, traces, and calibration.

No production threshold claims.

### J7M — held-out qualification

Freeze fresh held-out cases and human authority before model reveal.

Only this gate may support claims about:

- independent evaluator qualification;
- threshold validation;
- automation suitability.

## Non-claims

This ADR does not claim that:

- Jev is qualified as an autonomous adjudicator;
- Jev is unqualified in general;
- the existing 35-case calibration estimates general evaluator accuracy;
- any failure-label threshold is production ready;
- Final-342 should be rescored;
- the semantic-registry intervention improves evaluator performance.

Those claims require new measured evidence.
