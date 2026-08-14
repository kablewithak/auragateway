# Local ABC P4/P5 Cache-Context Repetition Differential Execution Authorization V1

## Purpose

Implement and validate the inert transaction-bound issuer for one future governed execution of the frozen 1x-vs-24x cache-context repetition differential.

## Design-only implementation boundary

During this tranche, only static issuer artifacts may be generated and validated. Do not run `authorize-generate`, create live lifecycle artifacts, generate a live notebook, observe Kaggle for a live transaction, load a model, start a worker, or issue a model request.

## Bound authorities

- authorization-design merge commit: `0ad27e48e72f91f52ca48927a66bbe44f099e258`
- authorization-design record SHA-256: `900b76c0cf8f833733f63c006e4aa489f9581d80260f4f30f6a4b9161c973a77`
- implementation merge commit: `658a21516fa6b1cc72bd53c2c65e51aae88b4d79`
- successor runtime SHA-256: `dfa0e7ea48eaf21dd6d3faf97b0440dda19817dec18de7c17d720c9185569a4b`
- implementation review SHA-256: `6bf7595e9dda3793f94bf866e0feff8db31cfe2c4c9cd7e3f4941c973a4ea2a4`
- implementation record SHA-256: `31628aef52b292236bbaf9a787fd1f47ca3751a1416cf916b51fc354258e4a6c`

## Human authorization flow after merge

1. Synchronize clean `main` with `origin/main`.
2. Invoke the merged issuer's `authorize-generate` command.
3. The issuer prepares a fresh intent and prints its dynamic SHA-256 challenge plus exact scope and execution budgets.
4. The operator manually retypes the exact challenge.
5. Exact match and freshness permit creation of one live single-use authorization and one transaction-bound notebook artifact.
6. Persist the durable T4 x2 / Internet Off platform-observation receipt.
7. Only after that receipt exists may the single Save & Run All proceed.

The challenge may not be synthesized by the assistant, model, runtime, or issuer automation.

## Frozen execution contract

The live authorization must retain the exact 1x-vs-24x experiment contract and a maximum of six model requests, six model loads, six fresh worker starts, zero hidden retries, zero replacement workers, zero external network requests, and zero external spend.

## Static validation order

1. Ruff format candidate-owned mutable Python.
2. Ruff check candidate-owned mutable Python.
3. Focused mypy.
4. Deterministic issuer `generate`.
5. Deterministic issuer `validate`.
6. Focused issuer pytest.
7. Validate the generated wrapper is compilable and contains no unresolved template markers.
8. Full repository pytest.
9. Authoritative immutable-lineage repository typecheck gate.
10. Re-run deterministic issuer validation after repository tests.
11. `git diff --check`.
12. Confirm the exact eight-path candidate boundary and staged/worktree byte identity.

## Non-authority

`live_authorization_issued=false`

`runtime_execution_authorized=false`

`platform_observation_persisted=false`

`kaggle_execution_performed=false`

## Next gate

`MERGE_THEN_ISSUE_FRESH_P4_P5_CACHE_CONTEXT_REPETITION_DIFFERENTIAL_EXECUTION_AUTHORIZATION_V1`
