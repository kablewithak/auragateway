# ADR: Exact-Runtime P5/P6 Provenance Identity Reconciliation V1

**Date:** 2026-08-10
**Status:** Proposed for correction tranche

## Context

Post-merge repository certification found that two static documentation identities
recorded by the Exact-Runtime P5/P6 implementation review and implementation
record never matched the bytes committed to Git.

The committed implementation ADR and report are unchanged from the historical
implementation merge. The implementation source, runtime template, tests,
runbook, implementation review, implementation record, notebook, runtime script,
wrapper, and all accepted authorities retain their historical identities.

No live P5/P6 execution authorization has been issued and no governed P5/P6
execution has occurred.

## Decision

Preserve the historically merged executable artifacts and their existing
identities. Do not regenerate the runtime script or notebook merely because two
non-executable documentation identity claims were captured before their final
committed bytes.

Add a deterministic provenance reconciliation record that:

- binds the actual committed ADR and report identities;
- records the two stale historical identity claims;
- proves the remaining static implementation artifacts are unchanged;
- preserves the historical implementation review, record, notebook, runtime,
  and wrapper identities;
- revalidates the semantic boundary against the runtime bytes embedded in the
  historical notebook;
- remains valid only while no live or terminal authorization artifact exists.

The execution-authorization issuer must bind the exact reconciliation source,
tests, and record before live issuance. The live authorization payload must carry
the reconciliation-record SHA-256 in addition to the existing historical
implementation and runtime bindings.

## Consequences

The correction makes provenance truthful without changing executable runtime
bytes or rewriting the frozen authorization design. The historical review's two
documentation claims are superseded only for the explicitly corrected paths.

A future execution remains unauthorized until the correction tranche is merged,
the issuer is revalidated on synchronized clean `main`, fresh platform evidence
is observed, and the operator supplies the exact fresh confirmation.
