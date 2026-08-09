# Runbook: Exact-Runtime P5/P6 Requalification Design V1

## Purpose

Generate and validate the deterministic design record only. This runbook performs no model,
worker, Kaggle, GPU, or authorization action.

## Local validation sequence

1. Start from clean synchronized `main` containing PR #228.
2. Create a feature branch.
3. Add the design source, tests, ADR, report, and runbook.
4. Generate the design record with the repository virtual environment.
5. Run changed-file Ruff lint/format checks.
6. Run `py_compile` and focused mypy for the authored design source.
7. Run the focused unit test file.
8. Run repository pytest and baseline-aware repository mypy according to current policy.
9. Freeze exact candidate bytes, stage exact paths, and verify the staged index.
10. Commit, verify, push, manually open the PR, merge, synchronize `main`, prove ancestry, and
    clean up the feature branch.

## Hard stop

Do not issue runtime authorization and do not execute Kaggle/model requests in this tranche.
After merge, the next gate is `implement_exact_runtime_p5_p6_requalification_v1`.
