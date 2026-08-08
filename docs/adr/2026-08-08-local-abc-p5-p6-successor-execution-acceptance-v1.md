# ADR: Accept governed P5/P6 successor runtime qualification V1

Date: 2026-08-08

## Status

Accepted candidate pending merge.

## Context

Two earlier technically successful successor runs were reconciled as ungoverned
and remain non-acceptance evidence. Saved version `340976295` followed the
required sequence:

fresh Kaggle capability observation → explicit operator confirmation →
single-use authorization issuance → authorization verification → one saved
version execution → terminal PASS → authorization consumption.

The consumed receipt binds saved version `340976295`, the exact authorization,
the runtime evidence ZIP, and the terminal log.

## Decision

Preserve the governed run byte-for-byte and accept it as the current-line P5/P6
successor runtime qualification pass only if repository authority, lifecycle
binding, archive safety, member bytes, P5 semantics, P6 semantics, execution
budgets, teardown, cleanup, and deterministic acceptance outputs all validate.

On acceptance:

- `current_line_p5_pass_accepted=true`
- `current_line_p6_pass_accepted=true`
- `measured_abc_eligible=true`

Acceptance does **not** issue measured A/B/C authority:

- `runtime_execution_authorized=false`
- `measured_abc_execution_authorized=false`

## Evidence identities

- saved version: `340976295`
- authorization SHA-256: `1567adabaf6ecd9a586c40c1f037914c54b24d1905a9553713e7c4ef1cab66ef`
- consumption SHA-256: `77c0d200010770fa4ff49b35d13678eccd07dea59ffc37b0f80567d5198026af`
- evidence ZIP SHA-256: `ed6a3c5b33b5a982a0793231db753a283c9d626f92d5eb8831a3fa1605ce88b6`
- terminal log SHA-256: `223e4d2d17536a9d33d31b07ed11d374408d2c2d28456d430b9c835539b5c0e1`

## Consequences

Measured A/B/C may move from **blocked by P5/P6 qualification** to **eligible
for a separately designed and merged authorization tranche**. Eligibility is
not execution authorization.

The two historical ungoverned technical passes remain immutable reconciliation
evidence and are not rewritten by this acceptance.
