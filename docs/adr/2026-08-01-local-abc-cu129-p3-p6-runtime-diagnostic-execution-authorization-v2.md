# ADR: P3-P6 Runtime Diagnostic Execution Authorization V2

## Status

Accepted for repository implementation only. Runtime authority is not issued by this change.

## Context

P3-P6 Runtime Diagnostic V2 is merged at `87f2d4e08043c0c6ec5dee93d14c0523f531e8fe` and binds the generated notebook SHA-256 `912b1888d110a0996122e57dfb8992748f6c0d531472b05339eca64ad43debdd`. The V2 implementation preserves bounded pip diagnostics, deterministic NOT_RUN probe reports, scratch cleanup evidence, and a 2 MiB evidence ZIP ceiling.

The previously accepted V1 run failed at the offline installation boundary. Its exact subprocess root cause remains unresolved; this authorization must not convert the V2 remediation into a retrospective V1 root-cause claim.

## Decision

Implement a separate, transient, single-use V2 execution authorization with:

- explicit operator confirmation;
- exact merged-main, feature-commit, notebook, request, implementation-record, model and wheelhouse identities;
- a maximum 240-minute validity window;
- one Kaggle session and one installation attempt;
- no external network requests, credentials, customer data, benchmark trajectories, hidden retries or external spend;
- mandatory consumption for PASSED, FAILED or INTERRUPTED outcomes;
- unchanged replay prohibited;
- authorization and consumption artifacts required to remain untracked.

## V2-specific controls

The authorization additionally binds:

- `wheelhouse/wheels` as the offline find-links scope;
- a required runtime installation report;
- bounded installation subprocess diagnostics;
- deterministic NOT_RUN reports for blocked probes;
- a scratch cleanup report;
- an allowlisted evidence ZIP no larger than 2 MiB.

## Consequences

The merged issuer can validate, issue, verify and consume one V2 authority. It does not execute Kaggle, install the runtime, load a model, start a worker or issue a model request. A separate explicit operator confirmation remains required after merge.
