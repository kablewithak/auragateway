# B-vs-D Marker-Diversified Differential Execution Authorization V1 Runbook

## Current gate

`IMPLEMENT_AND_MERGE_B_VS_D_CUMULATIVE_LENGTH_LOCKED_MARKER_DIVERSIFIED_DIFFERENTIAL_EXECUTION_AUTHORIZATION_ISSUER_V1`

The issuer tranche is static-only. Do not issue live authorization from the feature branch.

## Static implementation boundary

Expected candidate paths:

1. `.gitattributes`
2. issuer source
3. transaction-bound wrapper template
4. focused issuer test
5. producer-owned static review
6. producer-owned static record
7. issuer report
8. issuer runbook

Status must remain:

`IMPLEMENTED_NOT_ISSUED`

## Validation order

1. Governed Ruff format check on changed Python.
2. Governed Ruff lint on changed Python.
3. Python compilation.
4. Focused mypy on mutable issuer source and focused test.
5. Deterministic issuer `generate`.
6. Deterministic issuer `validate`.
7. Focused issuer pytest.
8. Verify all live lifecycle artifacts are absent.
9. Authoritative immutable-lineage typecheck policy validation.
10. Authoritative immutable-lineage repository typecheck gate.
11. Full repository pytest.
12. Re-run deterministic issuer validation.
13. `git diff --check`.
14. Prove exact eight-path candidate boundary and zero changed notebooks.
15. Stage only the eight expected paths.
16. Prove staged/worktree Git-blob byte identity.
17. `git diff --cached --check`.
18. Commit and push as separate transitions.

Do not substitute raw repository-wide `python -m mypy` for the immutable-lineage typecheck gate.

## Frozen future live issuance controls

Future issuance may occur only after the issuer is merged and local `main` is synchronized cleanly.

Live issuance requires:

`RETYPE_DYNAMIC_SHA256_CHALLENGE`

The challenge must be fresh and dynamically derived from the exact authorization intent. The operator must manually retype the exact challenge.

The assistant, model, runtime, or issuer automation must not synthesize the confirmation.

The future transaction must bind the merged issuer commit, issuer source, authorization design, implementation authorities, successor runtime payload, transaction-bound wrapper generator, exact runtime/model contract, B-vs-D experiment contract, 6/6/6 budget, platform policy, and authorization window.

## Platform observation

After transaction-bound artifact generation and before Save & Run All, persist:

`PERSIST_DURABLE_OBSERVATION_BEFORE_SAVE_AND_RUN_ALL`

Required fields:

- transaction ID
- platform observation timestamp
- accelerator
- allocated GPU count
- Internet state
- capability source

Console-only evidence is insufficient.

## Prohibited during this tranche

- live authorization issuance
- human challenge confirmation
- live transaction ID
- live governed executable generation
- durable live platform observation
- Kaggle session or Save & Run All
- runtime installation
- model load
- worker start
- model request
- B-vs-D execution
- threshold search
- runtime remediation
- P5/P6 requalification
- final A/B/C measurement

## Next gate after merge

`MERGE_THEN_ISSUE_FRESH_B_VS_D_CUMULATIVE_LENGTH_LOCKED_MARKER_DIVERSIFIED_DIFFERENTIAL_EXECUTION_AUTHORIZATION_V1`
