# AuraGateway Gate 6 Blinded Quality Preparation

## Purpose

This artifact records the second Gate 6 implementation boundary: deterministic preparation for condition-blind residual-quality review and independent adjudication.

It sits after deterministic quality scoring and before protected review execution.

## Runtime boundary

The workflow is:

1. validate the candidate with deterministic quality scorers;
2. place protected content in a pre-blinding source envelope;
3. map the episode to an opaque review assignment;
4. strip provider, model, condition, route, cost, latency, cache, and run-order fields;
5. send only the approved reviewer-visible fields to the protected review surface;
6. record primary and secondary reviews against the frozen rubric;
7. detect material disagreement;
8. require an independent adjudication record when needed;
9. retain only metadata-safe evidence in public reports.

## Frozen rubric

The rubric contains seven criteria:

- task correctness;
- evidence grounding;
- source use;
- terminal decision;
- completeness;
- clarity;
- safety.

Each criterion is scored from one to four.

A passing review requires:

- total score of at least 21;
- no criterion below two;
- no retained failure label.

A reviewer cannot use hidden reasoning as evidence. Protected evidence-note and rationale content is represented by SHA-256 digests in retained records.

## Assignment evidence

The frozen assignment manifest contains:

- 18 primary review assignments;
- 5 secondary review assignments;
- 23 total assignment slots;
- opaque review IDs;
- assignment-key SHA-256 digests;
- deterministic sampling seed `20260712`.

The double-review sample is:

- `ep-func-002`;
- `ep-func-003`;
- `ep-func-004`;
- `ep-func-012`;
- `ep-func-015`.

The sample is produced by hashing the sampling seed with each episode ID, ranking those hashes, selecting five, and storing the selected IDs in sorted order.

## Material disagreement rules

Adjudication is required when:

- reviewer verdicts differ;
- any criterion differs by two or more points;
- failure-label sets differ.

Primary and secondary reviewer identities must be distinct. The adjudicator identity must differ from both reviewers.

Adjudication is rejected when no material disagreement exists.

## Deterministic fixtures

The fixture set contains 10 cases:

- 5 passing controls;
- 5 negative controls;
- 4 cases with material disagreement.

Covered controls include:

- single primary-review pass;
- independent double-review agreement;
- verdict disagreement with valid adjudication;
- material criterion-score delta with valid adjudication;
- failure-label disagreement with valid adjudication;
- source and assignment episode mismatch;
- review and assignment mismatch;
- reviewer-independence violation;
- adjudicator-independence violation;
- unnecessary adjudication.

## Evidence artifacts

The frozen asset directory contains:

- `rubric.json`;
- `assignment_manifest.json`;
- `fixtures.json`;
- `report.json`;
- `manifest.json`.

The manifest hash-binds:

- the rubric;
- the assignment manifest;
- the fixture set;
- the fixture report;
- the Gate 2 review protocol;
- the Gate 2 episode manifest;
- the deterministic Gate 6 quality manifest.

## Verification

Normal verification uses:

`python -m auragateway.evals.blinded_runner verify --repo-root .`

The build command is reserved for deliberate asset versioning:

`python -m auragateway.evals.blinded_runner build --repo-root .`

## Privacy and evidence controls

- No customer data is used.
- Fixture content is synthetic.
- Experimental condition fields are removed before reviewer export.
- Public reports contain no raw conversation or candidate-output content.
- Reviewer and adjudicator identities are represented by SHA-256 digests.
- Review rationale and evidence notes are represented by SHA-256 digests.
- Protected review content must remain access controlled and outside public traces.

## Gate status

This slice proves review preparation and adjudication-control behavior.

Gate 6 remains open pending:

- protected review execution;
- completed primary reviews;
- completed secondary reviews;
- actual disagreement and adjudication records;
- held-out aggregation;
- A/B/C task-quality non-inferiority evidence.

## Claim boundary

This evidence does not claim that human review has occurred, that reviewer agreement is sufficient, or that any model condition is quality non-inferior.
