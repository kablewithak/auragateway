# ADR: P4 Output-Contract Diagnostic V2 Execution Acceptance V1

## Status

Accepted for repository implementation.

## Context

P4 V2 was executed once under single-use Authorization V3 in Kaggle saved version
`340775383`. The governed run completed all 18 scheduled requests with no runtime
divergence. Cases A, C, E, and F each produced 3/3 exact-object responses with one
response hash and zero request errors. Cases B and D completed successfully at the
transport layer but returned markdown-fenced invalid JSON in all three observations.

The selection rule prefers the least constraining eligible configuration, so case A is
selected.

## Decision

Preserve and accept the exact governed execution evidence. Bind the acceptance to:

- saved version `340775383`;
- V3 authorization and consumption receipts;
- exact terminal log and governed evidence ZIP identities;
- exact P4 V2 notebook/runtime/model authorities;
- the complete A-F request order and case metrics;
- the successful native-origin, worker-startup, teardown, and cleanup gates.

The accepted P4 conclusion is diagnostic, not a production-reliability claim.

## Consequences

P4 V2 is accepted as a successful governed output-contract diagnostic. Case A becomes
the selected configuration for the next measured A/B/C design gate. No measured A/B/C
execution is authorized by this acceptance.

The native-origin claim remains deliberately narrow: `libcusparse` and `libnvJitLink`
were observed from the target runtime and no prohibited origin was observed. An ambient
CUDA runtime library was also observed and is retained as an explicit limitation.

## Rejected alternatives

- Do not replay saved version `340775383`.
- Do not retain the live V3 lifecycle files at their operational benchmark paths.
- Do not rewrite the terminal log to satisfy whitespace policy.
- Do not collapse B/D invalid-JSON behavior into a runtime failure.
- Do not generalize E/F JSON-schema success beyond this pinned configuration.
- Do not start measured A/B/C execution from this PR.
