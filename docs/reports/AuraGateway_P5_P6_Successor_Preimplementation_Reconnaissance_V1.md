# AuraGateway P5/P6 Successor Preimplementation Reconnaissance V1

Decision: `GO_FOR_SUCCESSOR_IMPLEMENTATION_WITH_FROZEN_COMPOSITION_RULES`

Main authority: `3939f17cf5263f54ebae022232bf6d7a6cd8ef8a`

## Resolved architecture
- Native environment: P4 V2 hardening.
- Worker topology/action budget: V5.
- P4 canary: selected case A only.
- P5: V5 evidence design plus historical V4 execution proof.
- P6: V5 typed route and metric isolation.
- Benchmark trajectories: prohibited.

## Highest-risk seam closed before coding
P4 filters CUDA stub paths and removes `LD_PRELOAD`; V5 did not. The successor must use P4 environment hardening.

## P5
Historical V4 evidence already demonstrates positive warm cached-prefix tokens and a full-process restart followed by a zero-cache baseline. Latency remains supporting evidence, not the pass criterion.

## P6
Historical V4 failed at response-contract validation after worker-1 transport, not basic two-worker startup. V5 correctly separates route transport, response envelope, per-worker metric deltas, counters, checkpoints, and teardown.

No Kaggle, GPU, model, worker, runtime authorization, or benchmark activity is performed by this tranche.
