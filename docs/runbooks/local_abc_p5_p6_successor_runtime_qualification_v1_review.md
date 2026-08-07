# P5/P6 Successor Runtime Qualification V1 Review Runbook

## Purpose

Validate and merge the repository review before implementing any successor runtime notebook or authorization issuer.

## Required repository state

- current P4 acceptance main commit is an ancestor of HEAD;
- exact predecessor Git blobs are unchanged;
- no runtime authorization is issued;
- no Kaggle execution occurs;
- no benchmark trajectory is executed.

## Validation

Run:

```text
python -m auragateway.local_abc.p5_p6_successor_runtime_qualification_v1_review validate-authorities --repo-root .
python -m auragateway.local_abc.p5_p6_successor_runtime_qualification_v1_review generate --repo-root .
python -m auragateway.local_abc.p5_p6_successor_runtime_qualification_v1_review validate-package --repo-root .
```

Then run focused Ruff, mypy, pytest, immutable-lineage typecheck, repository Ruff, and full repository pytest.

## Stop conditions

Stop on any predecessor blob drift, P4 selected-contract drift, altered V4/V5 evidence semantics, nonzero benchmark-trajectory permission, nonzero hidden retries, or any attempt to issue runtime/measured execution authority.

## Next gate after merge

`implement_and_merge_p5_p6_successor_runtime_qualification_v1`

Implementation remains separate from runtime authorization and execution.
