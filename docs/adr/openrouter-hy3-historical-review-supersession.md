# ADR: Supersede Mutable Bindings in Historical OpenRouter Hy3 Reviews

## Status

Accepted.

## Context

The historical OpenRouter Hy3 identifiability and capability-probe authorization reviews correctly froze their source and output hashes at creation time. Later terminal-continuity work legitimately replaced two governing documents:

- `docs/product/AuraGateway_OpenRouter_Hy3_Free_Tier_Validation_Mini_PRD.md`
- `docs/product/AuraGateway_v2_PRD_Cache_Aware_Agent_Runtime_Harness.md`

The old validators continued comparing those live paths against historical hashes. The authorization manifest also bound the authorization runner itself, so changing that validator caused a second self-hash failure.

## Decision

Add a typed supersession overlay that:

1. preserves both historical review and manifest files byte-for-byte;
2. delegates only the exact historical binding sites for the two superseded documents to the later terminal-continuity manifest;
3. preserves all other historical source and output hashes;
4. records the historical and current authorization-runner hashes explicitly;
5. keeps provider execution, benchmark eligibility, and claims closed.

The overlay does not update old hashes in place and does not make historical evidence mutable.

## Consequences

- Current governing documents can remain current without invalidating historical evidence.
- Drift in the later terminal-continuity manifest or delegated documents still fails closed.
- Drift in non-delegated historical evidence still fails against the original manifest.
- The modified authorization runner is validated against its explicit superseding hash while its historical hash remains preserved.
- Future immutable reviews should bind versioned snapshots rather than mutable live-document paths.
