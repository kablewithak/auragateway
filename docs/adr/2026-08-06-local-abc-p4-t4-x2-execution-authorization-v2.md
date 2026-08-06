# ADR: P4 T4-x2 Execution Authorization V2

## Status

Accepted for implementation. This change does not issue live V2 authority.

## Context

The merged V1 issuer bound `T4_X1`. The current Kaggle notebook UI exposed only
`GPU T4 x2`. The operator stopped before creating a saved version, installing the
runtime, loading the model, starting a worker, or making a model request.

The merged runtime already sets `CUDA_VISIBLE_DEVICES=0` for the worker and writes
`gpu_index=0` in the worker-startup report. The defect is therefore the platform
allocation contract and lifecycle gap, not the runtime worker topology.

## Decision

Implement authorization V2 with:

- platform allocation `GPU_T4_X2`;
- exactly two allocated GPUs;
- exactly one worker-visible GPU;
- `CUDA_VISIBLE_DEVICES=0`;
- worker GPU index `0`;
- GPU index `1` excluded from model-worker authority;
- one model load, one worker start, and eighteen requests unchanged;
- mandatory live platform-capability observation before issuance;
- a non-overwriting `ABANDONED_BEFORE_EXECUTION` receipt for V1;
- distinct V2 authorization and consumption paths.

## Consequences

T4 x2 allocation does not authorize two-GPU execution. The second allocated GPU
remains unused by the governed worker. The V1 authorization remains non-reusable
and must be preserved outside the repository with a governed abandonment receipt.
