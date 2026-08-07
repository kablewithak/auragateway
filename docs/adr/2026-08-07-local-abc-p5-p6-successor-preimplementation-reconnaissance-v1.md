# ADR: Freeze P5/P6 Successor Composition Before Implementation

## Status
Accepted for repository-only reconnaissance.

## Context
Main authority: `3939f17cf5263f54ebae022232bf6d7a6cd8ef8a`. P4 V2 passed with a hardened native-library boundary and selected case A. V5 contains the stronger P5/P6 topology and evidence harness. The remaining high-value risk is composition drift between those lines, not generic CUDA viability.

## Decision
Freeze a compatibility matrix before successor implementation. P4 V2 is the environment/native-library basis. V5 is the P5/P6 worker/evidence basis. P4 case A is the only P4 canary. Full process restart remains the P5 reset proof. Benchmark trajectories remain zero.

## Key seam finding
V5 inherits `LD_LIBRARY_PATH` without P4 V2's explicit CUDA-stub filtering and does not explicitly remove inherited `LD_PRELOAD`. The successor must adopt P4 V2 environment construction rather than copy V5 unchanged.

## vLLM 0.19.1 source review
Pinned source confirms prefix-cache statistics use token queries/hits and exposes explicit reset semantics in the metrics accumulator. The successor does not depend on namespace-only cache reset because its governed reset proof is a full worker-process restart.

## Consequence
Successor implementation becomes constrained composition. Any divergence from the matrix reopens review before runtime authorization.
