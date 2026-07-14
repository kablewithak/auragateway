# ADR: Delegate Mutable Governing Documents Through a Typed Supersession Overlay

## Status

Accepted.

## Context

The original AuraGateway v2 core terminal-review manifest correctly froze its evidence files and the governing documents that existed at core closure. Later, the independently authorized OpenRouter/Hy3 extension legitimately superseded three live continuity documents:

- `README.md`;
- `docs/product/AuraGateway_v2_PRD_Cache_Aware_Agent_Runtime_Harness.md`;
- `docs/session/AuraGateway_SESSION_BRIEF.md`.

The historical manifest still contained the original hashes for those paths. Its validator therefore rejected clean repository state after the later continuity merge. Updating the historical hashes would rewrite evidence history. Reverting the current documents would erase valid later continuity. Skipping the validator would weaken the evidence boundary.

## Decision

Keep the original terminal-review manifest byte-for-byte immutable and add a typed supersession overlay:

```text
historical core terminal manifest
├── source evidence, review, report, ADR, and publication PRD
│   └── validated against original hashes
└── README, core PRD, and session brief
    └── delegated to the OpenRouter/Hy3 terminal-continuity manifest
```

The validator must:

1. verify the original manifest hash against the overlay;
2. verify the superseding manifest hash against the overlay;
3. validate both manifests through typed contracts;
4. confirm the exact three delegated paths and hash-field mappings;
5. confirm each historical hash still matches the original manifest;
6. confirm each current hash matches the superseding manifest;
7. continue validating all immutable historical evidence against original hashes;
8. fail closed on missing overlays, manifest drift, path substitution, or document drift.

## Consequences

### Positive

- Historical evidence remains immutable.
- Current continuity documents can remain at the terminal `2.3.0` state.
- The old validator once again passes on clean current `main`.
- Later document drift remains detectable.
- The pattern supports future additive continuity without rewriting evidence.

### Negative

- Validation now depends on one additional typed overlay and one later manifest.
- Future continuity changes must create a new explicit supersession layer rather than editing this overlay silently.

## Non-decisions

This ADR does not:

- reopen either provider execution lineage;
- alter Groq or OpenRouter/Hy3 outcomes;
- authorize provider calls, pilot execution, or A/B/C benchmarking;
- modify the original terminal-review manifest;
- weaken source-evidence hash validation.
