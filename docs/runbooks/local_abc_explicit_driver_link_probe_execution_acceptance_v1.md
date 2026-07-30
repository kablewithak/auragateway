# Runbook: explicit driver-link probe evidence acceptance V1

## Boundary

```text
base main: 147c2a886af71a97d38474be5ffb718442e551e8
branch: feat/local-abc-explicit-driver-link-probe-acceptance-v1
Kaggle execution: prohibited
GPU execution: prohibited
```

## Candidate

The final repository candidate contains exactly eight paths:

```text
typed acceptance validator
focused regression tests
generated acceptance record
ADR
engineering report
runbook
immutable execution log
immutable evidence ZIP
```

## Workflow

1. Create the state-bound feature branch.
2. Apply the seven direct files.
3. Run bounded Ruff on the two Python files.
4. Generate the deterministic acceptance record.
5. Run semantic validation, focused gates and full repository gates.
6. Stage exactly eight paths.
7. Commit, push and create the pull request through the GitHub browser.
8. Merge with a merge commit.
9. Synchronize main and delete the feature branch.

## Immutable evidence

Do not edit, normalize, recompress or regenerate:

```text
ag-cu129-explicit-driver-link-probe-v2-339127349.log
ag-cu129-explicit-driver-link-evidence-v2-339127349.zip
```

The duplicate uploaded TXT log is intentionally not preserved because it is
byte-identical to the canonical `.log` file.

## Prohibitions

- no unchanged Kaggle replay;
- no P2 execution;
- no wheelhouse installation;
- no model or worker;
- no global linker-environment mutation;
- no CUDA toolkit stub linking;
- no GitHub CLI;
- no Kaggle CLI.

## Next gate after merge

`DESIGN_AND_IMPLEMENT_P0_P2_PLATFORM_DIAGNOSTIC_V2`
