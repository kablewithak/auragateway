# CUDA 12.9 4f3302d Harness Evidence Integration

## Inputs

- materializer saved version: `338367572`
- inspection saved version: `338369540`
- source commit: `4f3302df871d47fec81e25e9af9609c0e2c7812d`
- harness SHA-256: `a154f3453c55571fc7535b546e4a97a66756ceb1900b51c2fd1336fed981d307`
- manifest SHA-256: `69e662e7504ad92d8bb940de77efdadf265451e9af9b11d14bc8e3060d2da894`
- materialization record SHA-256: `ceb3d934a3fb04a2c4d4452d87fa86d15d7955fde7f9e7784f3af96d7eb61e3c`
- inspection ZIP SHA-256: `2574307d69c9cf8ab0316bdf5be13cbfdfa5ced0febde9d4da0d87bc7ddb3f34`
- launcher source SHA-256: `cf5ec98d24fae4f926ad9ecf5c4764f17a4e6f994cbebf26f58f701e26df1f03`
- launcher notebook SHA-256: `9f0a9de5702017799e58b96dcb322b03a8fbd4be284c74282b60c5e0bfd46af9`

## Integrated state

```text
CURRENT_CU129_HARNESS_EVIDENCE_INTEGRATED
operational_input_closure=PASSED
authorization_issued=false
gpu_execution_performed=false
model_requests_performed=0
```

## Required validation

Run the repository integration validator and confirm:

```text
status=CURRENT_CU129_HARNESS_EVIDENCE_INTEGRATED
operational_input_closure=PASSED
source_commit=4f3302df871d47fec81e25e9af9609c0e2c7812d
harness_directory_sha256=a154f3453c55571fc7535b546e4a97a66756ceb1900b51c2fd1336fed981d307
authorization_issued=false
next_gate=post_merge_fresh_cu129_authorization_rebind
```

Reject the integration if any canonical evidence member, manifest identity,
materialization identity, launcher identity, runtime adapter identity, worker
diagnostics identity, saved-version ID, or documentation binding drifts.

## Prohibited actions on this branch

- Do not issue or materialize a fresh authorization.
- Do not run the Kaggle GPU qualification launcher.
- Do not reuse the consumed historical authorization.
- Do not overwrite historical `56f3373` evidence or records.
- Do not claim worker readiness, inference success, or A/B/C completion.

## Post-merge gate

After this branch merges:

1. Synchronize clean `main`.
2. Capture the actual integration merge commit.
3. Rebind the issuer and authority graph to that merge commit.
4. Bind the readiness-review SHA-256 produced by this integration.
5. Run focused and repository-wide validation.
6. Issue one new time-bounded, one-use authorization only after explicit
   operator confirmation.
7. Generate the frozen control materializer and launcher from clean merged
   authority.
8. Run one fresh governed Kaggle T4 x2 qualification attempt.
9. Preserve and evaluate the resulting evidence before further execution.

Next gate: `post_merge_fresh_cu129_authorization_rebind`.
