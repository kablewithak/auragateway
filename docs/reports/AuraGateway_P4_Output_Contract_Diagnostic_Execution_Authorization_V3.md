# AuraGateway P4 Diagnostic Execution Authorization V3

## Purpose

Provide a fail-closed, single-use authorization boundary for the exact merged P4 Output-Contract
Diagnostic V2.

## Bound implementation

- implementation feature commit: `99bf5a4afff8ee1ee8ddecc1aff689173cb38bab`
- implementation merge commit: `d61a146a2503a5e6bfd3fadbf1dad65dcad402ac`
- recorded V2 source-main generation commit: `d76c47d12366ad9500ccec18dd3aebf9b23f7b66`
- notebook: `5efc4660dcfca451947189001fdf2c6efc86d2201faa91b9b145ef3219bca581`
- runtime script: `bde93ca8b684640d6c8baccbd7782cdb627e27449dce39597b42d0828f3ed34f`
- wrapper code: `09e37eca21069c8ef5822711854307541ccfd7b158f2ccd902f58bba5fbd3402`
- request: `b1c87f012dff5252f77548ed668115b0f0e7a2070edc88f75762368cde5f7fd1`
- implementation record: `9fbefc001af0a56995f903681c6afe251a2ce594fd21d760a26ee7783352f5c1`
- model snapshot: `84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94`

## Predecessor lifecycle

Authorization V2 was consumed by saved version `340622392` with outcome `FAILED`. It is bound by
its exact authorization and consumption receipts and is non-reusable. Authorization V1 remains
terminalized as `ABANDONED_BEFORE_EXECUTION`.

## Runtime boundary

The authorization binds:

- platform allocation `GPU_T4_X2`;
- one GPU-0 worker through `CUDA_VISIBLE_DEVICES=0`;
- backend `TRITON_ATTN` with no silent fallback;
- target NVIDIA library precedence and CUDA-stub exclusion;
- post-readiness `libcusparse` and `libnvJitLink` origin validation;
- bounded 128 KiB stream capture and disabled request logging;
- one exact hash-locked offline wheelhouse with 182 manifest entries and 176 wheels;
- the unchanged A-F matrix and exact eighteen-request order;
- the exact seventeen-artifact terminal evidence contract.

## Budget

One authorization window of at most 240 minutes permits one Kaggle session, one saved version, one
runtime installation, one import-closure probe, one model load, one worker start, and eighteen model
requests. It permits zero hidden retries, external network requests, benchmark trajectories, or
external spend.

## Lifecycle

`IMPLEMENTED_NOT_ISSUED -> ISSUED -> CONSUMED`

Passed, failed, interrupted, timed-out, and Kaggle-platform-terminated attempts all consume the
authorization. Authorization and consumption records are non-overwriting local artifacts and must
remain untracked. Unchanged replay is prohibited.

## Non-claims

No live authority or P4 V2 execution is created by this implementation. Worker readiness, Triton
kernel compilation, JSON-schema compatibility, case selection, measured A/B/C, deployment
readiness, and production readiness remain unproven.
