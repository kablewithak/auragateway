# ADR: Immutable-Lineage Typecheck Gate

## Status

Accepted for repository implementation; not yet merged.

## Context

Strict project-mode mypy reports one assignment diagnostic in the accepted P3-P6 V3 failure-acceptance source. That source is byte-bound by the accepted V3 record, which is itself pinned by the V4 diagnostic implementation and downstream execution-authorization issuer. Editing the source or adding a `pyproject.toml` override would invalidate governed authority identities.

## Decision

Add a standalone typecheck gate that runs the unchanged project mypy configuration and accepts exactly one diagnostic only when all of these remain exact:

- mypy distribution version `1.20.2`;
- `pyproject.toml` SHA-256;
- immutable V3 source SHA-256;
- diagnostic path, line, severity, message, code, and occurrence count;
- mypy exit code `1`;
- zero additional or missing diagnostics.

The gate uses a temporary mypy cache outside the repository and does not mutate accepted source or configuration bytes.

## Rejected alternatives

1. Edit the accepted V3 source: rejected because it triggers a V3 to V4 to authorization lineage migration.
2. Add a mypy override to `pyproject.toml`: rejected because pyproject bytes are pinned by Groq compatibility, preflight-v3, and CUDA harness-toolchain authorities.
3. Ignore the mypy exit code in shell: rejected because it cannot distinguish one reviewed immutable diagnostic from new regressions.
4. Disable all errors for the V3 module: rejected because it would conceal future diagnostics.

## Consequences

- New mypy diagnostics fail closed.
- Disappearance or mutation of the reviewed diagnostic fails closed and requires policy review.
- Upgrading mypy requires explicit policy review.
- The historical source remains immutable.
- This is a baseline-regression gate, not a claim that raw project-mode mypy exits successfully.
