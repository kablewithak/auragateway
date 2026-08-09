# AuraGateway Exact-Runtime P5/P6 Requalification Design Certificate V1

## Decision

The behavioral design boundary is frozen for repository implementation, subject to repository
validation and merge.

## Accepted current authority

- Final Offline Verifier V5 repository acceptance: exact runtime capability only.
- Exact resolution lock: Python 3.12, Torch 2.11.0+cu129, CUDA 12.9, vLLM 0.25.1+cu129.
- V5 semantic boundary: public evidence cannot feed semantic decisions.

## Historical precedent

The governed predecessor P5/P6 PASS at saved version 340976295 is retained only for controls,
operational topology, reconciliation, teardown, and hypothesis-ranking precedent. Its runtime-
sensitive metric interpretation is not current authority.

## Frozen behavioral contract

P5: positive same-worker reuse, negative-prefix bound, negative-worker isolation, and
full-process-restart reset, decided from typed cache-specific token observations.

P6: explicit route realization and state ownership across independently identifiable worker
generations, with exact request reconciliation and teardown.

Decision states are `PASS`, `FAIL`, and `AMBIGUOUS`. Ambiguous evidence never promotes to PASS.

## Non-claims

No model execution is authorized or performed by this design. P5/P6, pilot readiness,
measured A/B/C effects, and production readiness remain unproved.
