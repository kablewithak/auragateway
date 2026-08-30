# ADR: Final 342 Measured Protected-Review Design V1

**Date:** 2026-08-30
**Status:** Proposed for final-342 measured-review design acceptance
**Base main:** `b2a67efa3abca65031090f52712ec87e816a911f`
**Execution authority:** None

## Context

The final AuraGateway experiment is already frozen at 342 trajectories and
1,368 logical turns: 162 functional trajectories plus 180 runtime
microbenchmark trajectories. G10 requires 100 percent primary rubric review,
a 25 percent independent double-review sample using seed `20260712`, and
stratification by condition and terminal decision. Reviewers must remain blind
to condition, route, latency, cache, and monetary cost information.

The merged final execution producer intentionally retains only privacy-safe
public evidence such as output hashes, telemetry, admission, retries, failures,
and trajectory terminal state. Raw candidate content therefore cannot be
reconstructed from public evidence after execution.

Historical Gate 6 already provides the frozen seven-criterion rubric,
deterministic quality scoring, blinded export mechanics, material-disagreement
detection, and adjudication invariants. Its assignment manifest is episode
based and requires unique episode IDs, so it cannot directly represent 162
measured functional trajectories that repeat each episode across conditions
and replications.

## Decision

Adopt:

`FINAL_342_MEASURED_PROTECTED_REVIEW_DESIGN_V1`

The design is a thin measured-run successor to accepted Gate 6 machinery. It
must preserve experiment truth, prevent post-result review selection, and make
quality evidence sufficient before the one governed final execution is
interpreted.

## Review population

The review unit is one planned functional trajectory.

The 162 functional trajectories receive 162 primary assignment slots before
execution. The 180 runtime-microbenchmark trajectories are not a substitute
for the functional human-review benchmark and do not receive human rubric
assignments under this design.

Assignment is predeclared. Poor quality, high latency, unfavorable results,
execution failures, or missing protected material do not authorize replacement
cases.

## Secondary-review target

The frozen fraction is 25 percent. Because `162 * 0.25 = 40.5`, the design
uses the conservative ceiling:

`secondary_review_target_count = 41`

The exact 41-trajectory schedule must be materialized before execution-manifest
freeze and bound by `review_sample_schedule_hash` in the final manifest.

## Sampling strata

Sampling strata are:

`planned condition_id x frozen expected_terminal_decision`

The observed model terminal decision is an outcome and is never a sampling
input.

The frozen functional set contains 10 answer, 3 clarify, 3 escalate, and 2
refuse episodes. With three repetitions per condition, each condition contains
30 answer, 9 clarify, 9 escalate, and 6 refuse trajectories.

Use Hamilton largest-remainder allocation over the 12 strata. Each stratum
receives `floor(n / 4)` slots, then the remaining seats are assigned by
remainder descending. Equal remainders are broken by ascending SHA-256 of:

`auragateway-final-342-review-stratum-v1|20260712|{condition_id}|{expected_terminal_decision}`

The resulting allocation is:

| Condition | Answer | Clarify | Escalate | Refuse | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| A | 7 | 2 | 2 | 2 | 13 |
| B | 8 | 2 | 2 | 2 | 14 |
| C | 8 | 2 | 2 | 2 | 14 |
| **Total** | **23** | **6** | **6** | **6** | **41** |

Within each stratum, planned trajectories are ranked by ascending SHA-256 of:

`auragateway-final-342-review-secondary-v1|20260712|{run_id}`

The selected count for that stratum is taken from the front of the rank. A
selected trajectory that later has no reviewable candidate is not replaced.

## Opaque identity

The reviewer must never receive a raw final run ID because final run IDs expose
condition information.

The protected review item identity reuses the accepted domain-separated
primitive:

`SHA256("auragateway-final-342-protected-review-v1|" + run_id)`

Primary and secondary role assignments derive distinct reviewer-facing IDs
from the opaque item identity:

`SHA256("auragateway-final-342-measured-review-assignment-v1|" + review_item_id + "|" + role)`

The reviewer-facing assignment shape remains `review-<first-24-lowercase-hex>`
for compatibility with existing blinded-review contracts.

An internal protected linkage may map opaque review identity back to run
identity after review. That linkage stays local and is never reviewer-visible.

## Reviewer-visible payload

The reviewer may receive:

- opaque review/assignment identity;
- episode ID;
- the user-visible four-turn conversation;
- the candidate assistant outputs that actually occurred;
- terminal structured output;
- citation and retrieved source IDs;
- relevant evidence resolved from the frozen source inventory/corpus;
- metadata-safe deterministic quality results; and
- the frozen rubric identity.

The reviewer must not receive:

- raw final run ID;
- condition ID or condition fingerprint;
- route schedule or worker identity;
- cache namespace or cache telemetry;
- latency or TTFT/E2E measurements;
- monetary-cost fields;
- planned run order;
- the internal rendered runtime prompt; or
- expected-answer, required-claim, forbidden-claim, or hidden claim-registry
  material.

The human-review package therefore uses condition-invariant benchmark and
corpus material instead of exposing the treatment-specific rendered prompt.

## Capture boundary

Protected capture occurs when a successful response still exists in memory,
before it is irreversibly reduced to public-only metadata.

Protected turn capture is append-only. It must preserve the user-visible
conversation and candidate output needed for trajectory-level review without
changing the model's conversation or execution behavior.

A deterministic quality scorer may consume richer candidate state at the same
response/trajectory boundary, but deterministic failure does not remove a bad
candidate from review merely because the candidate performed poorly.

## Capture-failure semantics

Three states are distinct:

- `REVIEWABLE`: candidate output exists and required protected capture exists;
- `NOT_REVIEWABLE_EXECUTION_FAILURE`: no candidate exists because execution
  failed; and
- `EVIDENCE_INCOMPLETE`: a candidate exists but required protected capture
  failed.

Protected-capture failure is not a model-quality failure and must not mutate
model or conversation behavior. It may not be silent.

The original execution evidence remains retained. No replacement trajectory is
substituted. A protected-capture gap blocks establishment of final quality
non-inferiority and therefore blocks runtime-improvement claims. Any rerun
requires fresh execution authority and preserves the original run.

## Retention and deletion

Use event-driven minimization rather than an arbitrary calendar retention
period.

Raw protected review material may be deleted only after:

1. required primary review is complete;
2. required secondary review is complete;
3. all required material-disagreement adjudication is complete;
4. final quality-analysis inputs are materialized; and
5. the public safe receipt/digest is verified.

Deletion requires a deletion receipt. After deletion, retain only safe hashes,
opaque IDs, counts, review verdicts, criterion scores, failure labels,
adjudication metadata, and the deletion receipt.

## Reuse boundary

Reuse exactly where valid:

- frozen seven-criterion rubric;
- existing review verdict rules;
- material-disagreement detection;
- adjudication invariants;
- frozen corpus and source inventory;
- frozen episode definitions; and
- existing privacy/blinding doctrine.

Do not promote the historical 18-episode assignment manifest into final
measured authority. The unique-episode assignment builder and synthetic
reviewer export need thin measured successors. This design does not authorize a
redesign of the merged final execution producer.

## Consequences

After this design tranche:

- review-unit semantics are closed;
- the final secondary-review target is 41;
- the deterministic stratified allocation rule is closed;
- measured opaque identity semantics are closed;
- reviewer-visible and prohibited fields are closed;
- protected-capture failure semantics are closed;
- event-driven retention/deletion semantics are closed;
- no final schedule has yet been materialized;
- no protected exporter implementation has yet been written;
- no rehearsal has occurred;
- the execution manifest remains unfrozen; and
- final execution remains unauthorized.

## Next gate

`DEFINE_FINAL_342_ANALYSIS_CONTRACTS_V1`

The analysis contracts must now specify the exact typed inputs for execution
accountability, runtime eligibility, quality completeness and non-inferiority,
paired statistics, and claim classification before implementation spreads
across producer, protected-review, and analysis boundaries.
