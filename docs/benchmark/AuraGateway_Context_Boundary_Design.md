# AuraGateway Static-Anchor and Volatile-Append Boundary

## Purpose

This slice defines the context partition boundary required before canonical serialization and prefix fingerprinting.

## Static partition

The static prefix is an explicitly ordered registry of six hash-bound artifacts:

1. benchmark policy evidence;
2. frozen retrieval configuration;
3. diagnostic episode manifest;
4. blinded review protocol;
5. terminal-decision constitution;
6. Gate 2 evidence.

The registry rejects duplicate IDs, duplicate paths, missing anchor kinds, order gaps, changed artifact bytes, unsafe paths, and public trace exposure.

## Volatile partition

Runtime state is represented as an immutable append log. Each item contains identity, sequence, type, content hash, byte count, classification, retention state, and an optional reference to an earlier superseded item.

Supported item kinds are user turn, retrieved evidence, retained feedback, tool result, runtime state, and terminal decision.

The contract rejects in-place mutation semantics, sequence gaps, duplicate identities, forward supersession references, content after a terminal decision, PII, secrets, and raw public trace content.

## Evidence boundary

This slice proves typed separation, ordering, append-only behavior, artifact binding, and mutation rejection. It does not implement canonical serialization, HMAC prefix fingerprints, five-turn prefix stability, provider calls, or Gate 3 completion.
