# ADR: Integrate the 4f3302d CUDA 12.9 harness evidence

## Decision

`CURRENT_CU129_HARNESS_EVIDENCE_INTEGRATED`

Promote the exact hardened harness materialized from
`4f3302df871d47fec81e25e9af9609c0e2c7812d` as the active CUDA 12.9 qualification input.

## Bound authority

- directory SHA-256: `a154f3453c55571fc7535b546e4a97a66756ceb1900b51c2fd1336fed981d307`
- file count: `1095`
- total bytes: `11034996`
- mounted path: `/kaggle/input/notebooks/kabomolefe/ag-harness-materializer-cu129-v1/ag_harness_materializer_cu129_v1_output/auragateway_qualification_harness_4f3302d_v1`
- materializer saved version: `338367572`
- inspection saved version: `338369540`
- inspection evidence ZIP SHA-256: `2574307d69c9cf8ab0316bdf5be13cbfdfa5ced0febde9d4da0d87bc7ddb3f34`
- manifest SHA-256: `69e662e7504ad92d8bb940de77efdadf265451e9af9b11d14bc8e3060d2da894`
- materialization record SHA-256: `ceb3d934a3fb04a2c4d4452d87fa86d15d7955fde7f9e7784f3af96d7eb61e3c`
- launcher source SHA-256: `cf5ec98d24fae4f926ad9ecf5c4764f17a4e6f994cbebf26f58f701e26df1f03`
- launcher notebook SHA-256: `9f0a9de5702017799e58b96dcb322b03a8fbd4be284c74282b60c5e0bfd46af9`

## Controls

The source publisher, materializer, and inspection ran with Internet Off,
zero package installation, zero model requests, and no authorization.
The inspection validated metadata and immutable identities only.

The prior `56f3373` harness remains preserved as historical predecessor
evidence and is not treated as the active operational input.

## Authorization boundary

This feature branch does not possess its future integration merge commit.
No fresh authorization may be issued from this branch.

## Next gate

`post_merge_fresh_cu129_authorization_rebind`

After merge, bind the issuer to the clean synchronized integration merge
commit and the exact current manifest, materialization, runtime adapter,
worker diagnostics, launcher source, launcher notebook, and readiness review.

## Non-claims

CUDA compatibility, vLLM installation, model loading, worker readiness,
inference success, A/B/C measurement, latency improvement, cost reduction,
quality non-inferiority, and production readiness are not claimed.
