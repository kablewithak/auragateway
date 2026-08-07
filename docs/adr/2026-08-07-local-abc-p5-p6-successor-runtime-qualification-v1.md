# ADR: P5/P6 Successor Runtime Qualification V1

## Status

Approved for repository implementation. Runtime execution remains unauthorized.

## Context

P4 Output-Contract Diagnostic V2 is formally accepted from saved version 340775383 and selected case A: V4 prompt, repetition penalty 1.1, unconstrained output. However, the successor runtime line does not yet establish current P5 prefix-cache/reset behavior or complete P6 route and metric isolation.

The historical V4 P3-P6 run established P5, but failed at P6. V5 hardened the P6 harness, then failed at P4 before P5 or P6 executed. The P4 diagnostic repaired and selected the output contract but did not execute successor P5/P6.

The Option C decision requires P3-P6 runtime proof before successor qualification and measured A/B/C. Therefore the P4 acceptance next-gate label is insufficient by itself to authorize measured execution.

## Decision

Implement one bounded successor P5/P6 qualification package before any measured A/B/C authorization.

The package will reuse the V5 P6 evidence contract and bind the accepted P4 case-A output contract. It will not rerun the A-F selection experiment.

The runtime sequence is:

1. P3 canary: current worker startup, explicit TRITON_ATTN, native-origin prerequisites.
2. P4 canary: one case-A exact-object request.
3. P5: same-worker cold/warm prefix reuse plus full-process reset.
4. P6: dual-worker process, GPU, port, route, and metric isolation.

Maximum model requests remain five. Benchmark trajectories remain prohibited.

## Consequences

A pass can establish current successor P5/P6 evidence for one governed run. It cannot itself authorize the 342-trajectory benchmark. Pressure/fault diagnostics, variance/repetition freeze, execution-manifest freeze, and measured authorization remain later gates.
