# Runbook: P0-P2 platform failure classification V1

## Boundary

```text
base main: b9cc4b639a2b08595497f396f1a7aa5475a4f519
branch: feat/local-abc-p0-p2-platform-failure-classification-v1
saved version: 339111200
Kaggle execution during this tranche: prohibited
model execution: prohibited
full-run authorization: absent
```

## Apply order

1. Apply the state-bound package.
2. Run bounded Ruff remediation on the two new ordinary Python files.
3. Generate the canonical classification record from the three immutable
   evidence files.
4. Run the classification semantic validator.
5. Run focused Ruff, formatting, project-mode mypy, focused pytest, full Ruff,
   full pytest, immutable evidence identity checks, bounded diff checking, and
   exact candidate validation.
6. Stage the exact nine-path candidate.
7. Commit, push, review, merge, and synchronize clean main.

## Immutable evidence

Do not edit, normalize, trim, recompress, or regenerate:

```text
ag-cu129-p0-p2-execution-launcher-v2-339111200.log
ag-cu129-p0-p2-execution-launcher-v2-339111200.zip
ag-cu129-p0-p2-platform-evidence-v1-339111200.zip
```

The external Kaggle log may contain whitespace that is not source-code style.
Validate it by SHA-256 and exclude only that exact path from `git diff --check`.

## Next tranche

After merge, design and implement a separate explicit real-driver link-path
probe V2. That future tranche must remain model-free and must not consume a GPU
execution until its implementation, identities, source materialization, and
inspection have passed.

## Prohibitions

Do not rerun saved version `339111200`. Do not claim general Kaggle
incompatibility. Do not select a CUDA toolkit stub. Do not mutate global
linker environment variables silently. Do not run P2 before P1 passes. Do not
load a model, start a worker, issue a model request, or execute A/B/C.
