# Runbook: final exact-runtime offline verifier V4

## Purpose

Validate V4 implementation and its producer/consumer evidence boundary locally before any external
execution authorization exists.

## Local acceptance order

1. Ruff check and format the V4 source/test.
2. Run focused mypy.
3. Run focused pytest.
4. Generate deterministic implementation review and record.
5. Run `validate-implementation`.
6. Run `validate-preexecution-contract`.
7. Run repository-wide baseline-aware Ruff/mypy/pytest.
8. Freeze exact tranche bytes.
9. Stage, commit, push, merge, and revalidate on main.

## Critical regression

The repository copy of:

`benchmarks/local_abc/evidence/preflight_v3_exact_runtime_wheelhouse_materialization_v1/materialization_receipt.json`

must remain SHA-256:

`55bc8d078af9960d5f6a60bf7d9638820be9fdda0ee76754a9462d46eb053fe0`

and must pass the producer receipt contract without containing consumer-owned fields.

## Pre-execution gate

After merge:

`python -m auragateway.local_abc.preflight_v3_exact_runtime_offline_compatibility_v4 validate-preexecution-contract --repo-root .`

Required outcome:

`PREFLIGHT_V3_V4_PREEXECUTION_CONTRACT_VALID`

This command is local/static and does not authorize GPU execution.

## Prohibited actions

Before a later V4 authorization issuer is merged:

- no Kaggle V4 run;
- no wheelhouse rebuild;
- no dependency re-resolution;
- no V3 replay;
- no model load;
- no worker startup;
- no request;
- no P5/P6;
- no pilot;
- no measured A/B/C.

## V3 disposition

Saved version `341197546` is preserved as diagnostic evidence. Its authorization is consumed and
non-reusable. V3 must not be edited or replayed merely to obtain a green result.
