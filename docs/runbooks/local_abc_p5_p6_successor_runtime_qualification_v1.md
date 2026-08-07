# Runbook: P5/P6 Successor Runtime Qualification V1

## Purpose

Validate and publish the repository implementation only. This runbook does **not**
authorize or execute Kaggle runtime work.

## Preconditions

- repository is on a feature branch created from synchronized clean `main`;
- source main is `1ff193c386a2f21738299ad0ece7cc16cafc5a11`;
- no successor runtime authorization or consumption artifact exists;
- all seven accepted authority inputs retain their bound SHA-256 identities.

## Authored paths

1. `src/auragateway/local_abc/p5_p6_successor_runtime_qualification_v1.py`
2. `src/auragateway/local_abc/templates/p5_p6_successor_runtime_qualification_v1.py.tmpl`
3. `tests/unit/local_abc/test_p5_p6_successor_runtime_qualification_v1.py`
4. `docs/adr/2026-08-07-local-abc-p5-p6-successor-runtime-qualification-v1-implementation.md`
5. `docs/reports/AuraGateway_P5_P6_Successor_Runtime_Qualification_V1_Implementation.md`
6. `docs/runbooks/local_abc_p5_p6_successor_runtime_qualification_v1.md`

## Generated paths

The producer owns these files. Never hand-edit them.

1. `data/evals/benchmark/environment-qualification-v1/p5_p6_successor_runtime_qualification_v1_request.json`
2. `benchmarks/local_abc/auragateway_p5_p6_successor_runtime_qualification_v1_implementation_review.json`
3. `notebooks/auragateway_p5_p6_successor_runtime_qualification_v1.ipynb`
4. `benchmarks/local_abc/auragateway_p5_p6_successor_runtime_qualification_v1_record.json`

## Validation order

1. normalize authored Python with Ruff;
2. verify authored Python lint/format;
3. run focused mypy;
4. generate producer-owned artifacts;
5. lint and format-check the generated notebook;
6. run focused successor tests;
7. run producer validation;
8. run repository-wide Ruff;
9. run repository-wide pytest;
10. run producer validation again;
11. freeze exact ten-path identities;
12. stage only the ten governed paths;
13. verify staged path and blob boundaries;
14. run `git diff --cached --check`;
15. commit and push;
16. create the PR manually;
17. after merge, synchronize `main`, prove ancestry, validate, and delete branches.

Any authored-byte mutation after generation invalidates the implementation-record
receipts. Regenerate before advancing.

## Runtime prohibition

Do not:

- create a live execution authorization in this PR;
- run the generated notebook;
- attach customer/private data;
- enable Kaggle Internet;
- make any model request;
- execute an A/B/C trajectory.

The next legal gate after merge is a **separate single-use successor execution
authorization design/issuance**.
