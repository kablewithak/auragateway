# Runbook: P4 T4-x2 Execution Authorization V2

## Before candidate work

1. Preserve the exact V1 authorization outside the repository.
2. Confirm no Kaggle saved version exists.
3. Confirm no runtime installation, model load, worker start, or model request occurred.
4. Remove the archived V1 authorization from the repository working tree.
5. Keep the archive and intake manifest unchanged.

## Candidate validation

1. Generate the V2 review and record.
2. Verify the runtime template contains `CUDA_VISIBLE_DEVICES=0`.
3. Verify worker-startup evidence records `gpu_index=0`.
4. Run focused Ruff, focused pytest, immutable-lineage typecheck, repository Ruff,
   and full pytest.
5. Commit exactly seven static V2 paths.
6. Merge with a merge commit and synchronize clean `main`.

## Legacy abandonment

Run `abandon-v1` from merged synchronized `main` using the archived V1
authorization. Confirm:

- no saved version was created;
- no runtime execution occurred;
- observed Kaggle allocation was `GPU_T4_X2`.

The command writes one untracked, non-overwriting abandonment receipt.

## V2 issuance preflight

Observe the current Kaggle notebook settings immediately before issuance:

- accelerator `GPU T4 x2`;
- Internet off;
- one governed wheelhouse attached;
- one governed model snapshot attached.

Confirm the merged runtime worker contract:

- `CUDA_VISIBLE_DEVICES=0`;
- one visible worker GPU;
- worker GPU index `0`;
- GPU 1 receives no model worker.

## Execution

Run one saved version only. Do not edit the A-F schedule, retry requests, expose
GPU 1 to the worker, or create a second saved version. Consume V2 after PASSED,
FAILED, or INTERRUPTED.
