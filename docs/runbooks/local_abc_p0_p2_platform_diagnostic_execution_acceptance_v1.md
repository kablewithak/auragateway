# Runbook: P0-P2 platform diagnostic evidence acceptance V1

## Boundary

```text
base main:
1cabdacc6d98691fb734322830514d6566a98e8e

branch:
feat/local-abc-p0-p2-platform-diagnostic-acceptance-v1

Kaggle execution:
prohibited

GPU execution:
prohibited
```

## Candidate

The final candidate contains exactly eight paths:

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

## Immutable evidence

Do not edit, normalize, recompress or regenerate:

```text
ag-cu129-p0-p2-platform-diagnostic-v2-339140121.log
ag-cu129-p0-p2-platform-evidence-v2-339140121.zip
```

The extra uploaded TXT log is intentionally omitted because it is byte-identical
to the canonical `.log` file.

## Workflow

1. Create the state-bound feature branch.
2. Apply the seven direct files.
3. Run bounded Ruff on the two Python files.
4. Generate the deterministic acceptance record.
5. Run semantic, focused and full repository gates.
6. Stage exactly eight paths.
7. Commit, push and create the PR through the GitHub browser.
8. Merge using a merge commit.
9. Synchronize main and delete the feature branch.

## Prohibitions

- no unchanged Kaggle replay;
- no GPU execution;
- no attention-backend execution;
- no model or worker;
- no global linker-environment mutation;
- no CUDA toolkit stub;
- no GitHub CLI;
- no Kaggle CLI.

## Next gate after merge

`DESIGN_AND_IMPLEMENT_EXPLICIT_TRITON_ATTENTION_BACKEND_V1`
