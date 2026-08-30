# ADR: Final 342 Producer → Review → Analysis Seam Audit V1

## Status

Proposed for acceptance.

## Context

G11.4 established the final 342 execution producer. G11.5 froze the measured protected-review
design. G11.6 froze the post-run analysis contract. The remaining risk is architectural rather
than statistical: adding review and analysis successors at the wrong boundary could mutate the
accepted producer, duplicate durable evidence, expose condition identity to reviewers, or create
post-hoc reconstruction paths.

The seam audit therefore asks one narrow question: which required final-342 inputs already exist,
which exist only transiently, and which still require explicit successor implementations?

## Decision

Do not modify the accepted execution producer at this gate.

The existing producer already exposes the required protected-review interception seam:
`execute_transport_attempt(...)` returns `TransportExecutionResult`, which carries the transient
decoded `response_object` and its JSON-validity flag. The transport outcome is durably persisted
before that result is returned. The public producer state and evidence bundle deliberately retain
hashes and measurements rather than raw outputs.

This is the correct split. The protected-review successor can consume the transient response after
transport persistence while keeping raw review material outside the public producer bundle.

The next implementation boundary is therefore `FINAL_342_MEASURED_REVIEW_SUCCESSOR_V1`.

That successor owns two coupled responsibilities:

1. materialize the exact 41-run secondary-review schedule from the frozen 162 functional runs,
   using the accepted Hamilton allocation and deterministic within-stratum SHA-256 ranking; and
2. implement append-only protected turn capture and reviewer export at the accepted successful
   response boundary, with opaque identities and a public digest-only receipt.

The schedule is derivable entirely from frozen planned-run and episode inputs. It does not depend
on observed model outcomes and therefore does not require execution authority.

## Remaining successors

After the measured-review successor, the remaining missing boundaries are:

- measured task-success reducer;
- unsafe-behavior regression reducer;
- measured feedback successor; and
- final analysis engine.

The historical quality and feedback contracts remain useful reference implementations, but their
synthetic schemas are not direct measured-run inputs.

The analysis engine remains deferred until the review, quality, and feedback inputs exist. The
offline orchestration and one meaningful integration rehearsal follow those implementations.

## Rejected alternatives

### Modify the final execution producer now

Rejected. Current evidence shows an existing transient response hook after durable transport
persistence. Producer mutation would increase regression surface without proving a missing hook.

### Persist raw outputs in the public producer bundle

Rejected. It would violate the accepted public-evidence minimization boundary and weaken reviewer
blinding/privacy controls.

### Select the 25% secondary review sample after execution

Rejected. The accepted design requires a predeclared 41-run schedule stratified by condition and
expected terminal decision, with no post-result replacement.

### Implement the analysis engine before review/quality/feedback successors

Rejected. That would create an engine whose required inputs are not yet production-shaped and
would invite manual reconstruction or synthetic-to-measured schema leakage.

## Consequences

The producer stays stable. The next tranche can be narrow and review-side. Manifest freeze,
execution authority, and effect claims remain false until all required successors and the offline
integration rehearsal are accepted.
