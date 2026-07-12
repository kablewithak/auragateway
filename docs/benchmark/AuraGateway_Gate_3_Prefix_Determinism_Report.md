# AuraGateway Gate 3 Prefix Determinism Report

## Decision

```text
Gate 3: PASS
Canonical serialization: implemented
HMAC-SHA256 fingerprinting: implemented
Five controlled turns stable: 5 / 5
Mutation controls passed: 7 / 7
Measured execution permitted: no
Required next gate: Gate 4 — Telemetry Integrity
```

## Frozen Prefix

```text
Serialization version: canonical-static-provider-v1
Template: nimbus-relay-support-template-v1@1.0.0
HMAC key ID: synthetic-prefix-fixture-key-v1
Prefix fingerprint:
6b7c72729eca9480ef7a0cf734b957dd6c10fa9ff88adc33e322af54d50f4d63

Canonical SHA-256:
9e95908cd14f8df3f667e7e3e36b2d928652cbe16a43477671068b5680a1bf5b

Canonical bytes: 24532
```

Component fingerprints:

```text
Tool contract:
178393f12dfc35f49d2fb3c1446fe5762f4661dba5c03109bbc92304490208e5

Output schema:
644781b8d2906a7b280c1b9c5abbe7957814c77902707c1facb2b6af5695f149

Context pack:
7da5fb07efaa398a628e9d55c140f7afcf9ef2413eeccbebb2d260d4e17a25c0
```

## Five-Turn Stability

The five controlled turns contain increasing volatile append logs with 1, 3, 5, 7, and 9 items.

Every turn produced the same static prefix fingerprint:

```text
6b7c72729eca9480ef7a0cf734b957dd6c10fa9ff88adc33e322af54d50f4d63
```

Volatile changes did not alter the static fingerprint.

## Mutation Calibration

| Mutation | Required outcome | Observed outcome | Result |
|---|---|---|---|
| Timestamp insertion | Block volatile leak | Blocked | Pass |
| Tool-order change | Fingerprint changes | Changed | Pass |
| Output-schema version change | Fingerprint changes | Changed | Pass |
| JSON key-order change | Canonically equivalent | Equivalent | Pass |
| One-byte static example change | Fingerprint changes | Changed | Pass |
| Volatile user-content change | Static fingerprint unchanged | Unchanged | Pass |
| Retrieval-order change | Static fingerprint unchanged | Unchanged | Pass |

The JSON-order case confirms canonicalization rather than treating semantically equivalent key order as a prefix mutation.

## Artifact Hashes

```text
Compiler specification:
b424353becc50f35356cb8795405e42d819e4e94492f57bcf6354dba7af05f9c

Static-anchor registry:
172006d5e574c79ff1ed5191eeb61788c9c2e9d6e3fed25cb1cfecbc9c718a4d

Context boundary manifest:
e6f990cfd9b1d3b482139ede48f531523819fed1e44cd8d9b8d3356e9bbbef77

Five-turn fixtures:
6d5f36ff23db905d7b810ec4810bce5ebc93b4042987d167d7e71791bc464f2d

Mutation cases:
026f895f3b4a147516b089ad47eb69b6bb1ebd34c69c09dd74d412e716c701eb

Stability report:
fefeffdba98be69521080166574ec627763a395463fb185880a2f96edeee7bde

Gate 3 manifest:
a8b4f3d3afc7708c828f9ac195b42cf97b90e7060c58cefe29d7bdc5aba6101b
```

## Validation

```text
Tests: 184 passed
Ruff: 0.15.20, passed
Strict mypy: passed across 72 source files
Historical artifact verifiers: passed
Context-boundary verifier: passed
Prefix-determinism verifier: passed
```

## Evidence Boundary

This report proves:

- deterministic provider-neutral static serialization
- HMAC-SHA256 prefix fingerprinting with environment-loaded key material
- five-turn static-prefix stability
- static/volatile isolation under controlled fixtures
- required mutation detection
- canonical equivalence for JSON key-order variation
- hash-bound reproducibility of Gate 3 evidence

It does not prove:

- provider cache hits
- provider telemetry integrity
- live request serialization parity
- latency or cost improvement
- route-policy safety
- task-quality safety under model execution
- measured benchmark readiness
- production readiness
