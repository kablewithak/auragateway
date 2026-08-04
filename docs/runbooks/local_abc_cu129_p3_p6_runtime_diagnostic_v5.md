# Runbook: Local A/B/C CU129 P3-P6 Runtime Diagnostic V5

## Current tranche

Repository implementation only. Do not execute Kaggle and do not issue runtime
authority from this tranche.

## Preconditions

- branch created from `40b3530a763465fee0f7e27db17e9c444436ca18`;
- clean worktree and index before applying the candidate;
- accepted V4 failure record, review, implementation record, and template match
  their pinned SHA-256 identities;
- V5 operational authorization and consumption paths are absent.

## Candidate paths

The generator exports exactly ten paths: source, template, tests, ADR, report,
runbook, request, review, notebook, and implementation record.

## Local validation order

1. apply the six authored files;
2. run bounded Ruff fix and format on the V5 source and test only;
3. compile the source, template, and test;
4. run the focused V5 tests;
5. run the V5 generator;
6. freeze the ten-path candidate;
7. run read-only V5 validation;
8. run project-mode mypy;
9. run repository Ruff and pytest;
10. validate the exact staged tree before commit.

## Required runtime behavior after later authorization

- P4 continues exact structured-output validation;
- P6 checkpoints request attempts before transport;
- P6 route acknowledgement uses transport plus isolated metrics;
- raw prompts and raw model outputs are never retained;
- no retry occurs after failure;
- both worker process trees receive native-origin inspection;
- terminal teardown and scratch cleanup always execute;
- any terminal run consumes its authorization.

## Publication

PowerShell stops after push and remote verification. The user creates and merges
the pull request manually in GitHub.

## Non-claims

Local generation and tests do not prove Kaggle execution, environment
qualification, measured cache effect, deployment, or production readiness.
