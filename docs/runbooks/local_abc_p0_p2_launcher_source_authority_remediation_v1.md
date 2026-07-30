# Runbook: P0-P2 launcher source-authority remediation V1

## Boundary

```text
base main: d3c111a94ae517763d51fc724702bd9a3c11dd52
branch: fix/local-abc-p0-p2-launcher-source-authority-v1
failed Kaggle saved version: 339098285
Kaggle execution during remediation: prohibited
full-run authorization: absent
```

## Apply order

1. Apply the state-bound package.
2. Run bounded Ruff repair on the four changed ordinary Python files.
3. Generate the remediation record from immutable failed-run evidence.
4. Regenerate the launcher record and notebook through the launcher producer.
5. Run remediation and launcher semantic validators.
6. Run focused Ruff, formatting, project-mode mypy, focused tests, full Ruff,
   full pytest, Git diff validation, and exact candidate-boundary validation.
7. Stage the exact candidate, commit, push, review, merge, and clean-sync main.

## Corrected replay

After merge, preserve the failed notebook under
`ag-cu129-p0-p2-exec-failed-v2`. Upload the newly generated launcher under the
canonical title. Attach exactly:

1. corrected source materializer saved version `339075357`;
2. governed CUDA 12.9 wheelhouse materializer saved version `1`.

Use T4 x2, Internet Off, no secrets, and one Save & Run All execution.

## Prohibitions

Do not rerun saved version `339098285` unchanged. Do not attach inspection
output, model snapshot, authorization, standalone source Dataset, or a third
input. Do not load a model, start a worker, issue requests, or run benchmark
trajectories.
