# ADR: P3-P6 Runtime Diagnostic Execution Authorization V4

## Status

Accepted for repository implementation only.

## Context

P3-P6 Runtime Diagnostic V4 is merged at main commit
`603f11bf10336222d289d56d29a18d3e9c705c68`. It hardens backend-marker,
capture-finalization, worker/GPU identity, teardown, and executed runtime-source
evidence. The implementation remains `IMPLEMENTED_NOT_EXECUTED` and does not
include runtime authority.

The accepted V3 attempt remains a consumed `FAILED` lifecycle. Its reported
backend failure is quarantined as an invalid diagnostic and may not be replayed
unchanged.

## Decision

Implement a separate repository-native V4 authorization issuer with strict
Pydantic v2 contracts and a transient, non-overwriting, single-use authority.

Bind issuance to:

- merged V4 main and feature commits;
- exact V4 implementation record, request, review, notebook, template and
  implementation source identities;
- exact notebook wrapper and embedded runtime-script identities;
- exact model snapshot and offline wheelhouse controls;
- the complete V4 evidence contract and action budget;
- explicit operator confirmation;
- synchronized clean `main`;
- absence of any prior V4 consumption receipt.

A `PASSED`, `FAILED`, or `INTERRUPTED` attempt consumes the authority. The
operational authorization and consumption receipt must remain untracked and be
preserved later with runtime evidence.

## Consequences

This tranche does not issue live authorization or execute Kaggle. After merge,
one explicit operator-confirmation workflow may issue and verify one bounded
V4 authority. Unchanged replay remains prohibited.
