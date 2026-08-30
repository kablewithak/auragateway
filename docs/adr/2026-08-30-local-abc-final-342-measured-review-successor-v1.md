# ADR: Final-342 Measured Review Successor V1

Date: 2026-08-30

## Status

Proposed for acceptance.

## Context

The accepted G11.7 seam audit established that the final-342 execution producer already exposes
the required transient response object after durable transport persistence. It also established
that producer modification is not the first missing boundary. The two review-side gaps are the
exact 41-run secondary-review schedule and a measured protected-review capture/exporter.

The exact secondary schedule is deterministic from the frozen 162 functional trajectories,
expected terminal decisions, the accepted 20260712 seed, and Hamilton allocation. The mapping is
review-sensitive, so this successor persists the exact schedule under the protected `.local`
review root and commits only its deterministic SHA-256 digest.

## Decision

Implement `FINAL_342_MEASURED_REVIEW_SUCCESSOR_V1` as a review-side successor without modifying
the final execution producer.

The successor:

1. derives the exact 41-run schedule from the accepted G11.7 derivation and G11.5 allocation;
2. binds the deterministic protected schedule bytes to SHA-256
   `9566edb218c2d9c6459e8428bc93676bc1e73484b2fd56a249aed2cc1db6748c`;
3. materializes those bytes only under
   `.local/auragateway/final-342-protected-review-v1/review_sample_schedule_v1.json`;
4. consumes the transient `TransportExecutionResult.response_object` after durable transport
   persistence;
5. stores raw turn captures append-only in the protected root;
6. builds primary reviewer payloads for every reviewable candidate and secondary payloads only for
   the predeclared 41-run schedule;
7. rejects reviewer payloads containing condition, route, worker, cache, latency, cost, planned
   order, internal rendered prompt, or expected-answer metadata;
8. returns a digest-only public receipt whose item count means unique review items;
9. permits raw protected-material deletion only after review, adjudication, analysis-input, and
   public-receipt gates are all complete.

## Consequences

The producer remains transaction-bound and unchanged. Review capture failure remains
`EVIDENCE_INCOMPLETE`, not a model failure, and does not permit replacement. The review schedule is
predeclared and outcome-independent. The public evidence surface does not gain raw prompts, raw
outputs, provider payloads, or condition-bearing review mappings.

The schedule must be materialized and verified during the acceptance gate before this tranche is
considered complete. Manifest freeze remains prohibited. Final measured A/B/C execution remains
unauthorized.

## Rejected alternatives

Publishing the full run-to-review schedule in the public evidence bundle was rejected because the
accepted review design requires reviewer-facing treatment blinding and only requires the final
manifest to bind the schedule hash.

Modifying the execution producer was rejected because G11.7 validated the existing transient
response hook as sufficient.

Post-outcome sampling, replacement review cases, and silent capture failure remain prohibited.

## Next gate

`AUTHOR_FINAL_342_MEASURED_QUALITY_REDUCERS_V1`
