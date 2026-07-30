# Runbook: P0-P2 Source Acceptance Integration V1

## Repository boundary

```text
branch: feat/local-abc-p0-p2-source-acceptance-v1
base main: 0257678b9b6c0afc89927dd24b45cebfe1ab311f
authorization: absent
Kaggle execution during integration: prohibited
```

## Apply order

1. Apply the state-bound package.
2. Run bounded Ruff fix and format on the four changed ordinary Python files.
3. Generate the acceptance record from the evidence validator.
4. Generate the launcher notebook and record through the launcher producer.
5. Run acceptance and launcher semantic validators.
6. Run focused Ruff, project-mode mypy, focused tests, full repository gates, and exact
   candidate-boundary validation.
7. Stage the exact validated candidate, record the staged tree SHA, commit, push, and
   verify the remote branch.

## Accepted versions

```text
materializer saved version: 339075357
inspection saved version: 339077364
```

## Generated-artifact rule

Do not edit the acceptance record, launcher record, or launcher notebook directly.
Regenerate them through their owning Python modules. Do not directly format generated
notebooks or canonical JSON records.

## Post-merge gate

After clean-main synchronization, configure the launcher with:

```text
Accelerator: T4 x2
Internet: Off
Secrets: None
Input 1: corrected materializer saved version 339075357 output
Input 2: governed CUDA 12.9 wheelhouse notebook output
```

Execute one saved version only. Preserve failure evidence and stop on the first failure.

## Prohibitions

- Do not attach the inspection output to the launcher.
- Do not attach a standalone source Dataset.
- Do not attach the model snapshot.
- Do not issue full-run authorization.
- Do not start a model or worker.
- Do not perform benchmark trajectories.
- Do not reuse GPU saved version `338921762`.
