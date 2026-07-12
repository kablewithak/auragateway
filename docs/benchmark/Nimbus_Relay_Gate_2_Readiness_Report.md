# Nimbus Relay Gate 2 Readiness Report

Decision: **PASS**
Gate: **Gate 2 — Diagnostic Eval Readiness**
Asset version: **1.0.0**

## Decision

AuraGateway Gate 2 passes because the functional and runtime diagnostic episode assets are frozen, development and held-out episodes are separated, every accepted episode has a concrete failure hypothesis, rejected proposals retain explicit reasons, and the blinded review protocol is prepared.

Measured runtime execution remains prohibited. The next proof gate is Gate 3, Prefix Determinism.

## Frozen Counts

```text
Functional episodes: 18
Development episodes: 12
Held-out episodes: 6
Runtime subset: 6
Rejected proposals: 8
Turns per episode: 4
```

Terminal decisions:

```text
answer: 10
clarify: 3
escalate: 3
refuse: 2
```

## Hash Evidence

```text
Retrieval freeze:
dc74b69b72cb5a392ce86f46d7b4709a5106746d84053ebff09b573b57271492

Retrieval configuration fingerprint:
220ce9ac6e19789bedf1aedc2b6253db5ba03a09ebcc6efdac203eb80cd23490

Functional episode set:
6229df94a6a426f815a2050172a79e115d9554031239043b397140ce13894285

Rejected proposal set:
80d846fcb2aea4a9e4a0cace81ca9b9875592ddc45c224c658ba87b1243adc5b

Runtime selection:
5ff912ad317fe09d97518e5b03178ebe3bb565dcf09719182bfffc80b67034e1

Blinded review protocol:
925e614c3a81d7e438299436ddf3619fa462cd861e0b816f26937279506ab3af

Episode manifest:
3a77c6fa037c62a1a548c2e5dc13e9668ebd3114cb58903df538bf7fa239ea6b
```

## Gate 2 Checks

| Check | Result |
|---|---|
| Development and held-out assets separated | Pass |
| Every accepted episode has a failure hypothesis | Pass |
| All required diagnostic families represented | Pass |
| Exactly 18 functional episodes | Pass |
| Exactly four turns per episode | Pass |
| Exactly six runtime episodes | Pass |
| All terminal decisions represented in runtime subset | Pass |
| Required and forbidden source scopes validate | Pass |
| Source IDs exist in the frozen corpus | Pass |
| Rejected proposals retain reasons | Pass |
| Blinded review protocol prepared | Pass |
| Retrieval freeze binding validates | Pass |
| Public-trace raw-content prohibition retained | Pass |
| Measured execution remains prohibited | Pass |

## Diagnostic Coverage

The set covers version conflicts, similar errors, missing parameters, incomplete documentation, repeated information, contradictory corrections, duplicate evidence, noisy context, unsupported behaviour, capability boundaries, multi-turn correction, provider failure, multi-source grounding, and SDK variant correction.

## Runtime Subset

The six selected episodes represent all four terminal decisions. The subset is frozen now so later latency and cache comparisons cannot cherry-pick easier trajectories after results are observed.

## Review Readiness

The review protocol is prepared but no model output has been reviewed. Reviewers will be blinded to experimental condition and runtime metrics. Five of the 18 functional episodes will receive independent double review using seed `20260712`.

## Non-Claims

Gate 2 does not establish:

- task-success rate;
- structured-output validity;
- citation-support performance;
- feedback retention;
- prefix determinism;
- provider telemetry integrity;
- route-policy safety;
- measured cost or latency improvement;
- production readiness.

## Next Gate

Gate 3 requires a typed static-anchor registry, volatile-append contract, canonical serialization, HMAC prefix fingerprinting, mutation audits, and a five-turn prefix-stability report.
