# Runbook: P3-P6 runtime diagnostic failure acceptance V4

## Purpose

Validate and commit the preserved failure evidence for Kaggle saved version
`340120168`. This runbook does not authorize or perform runtime execution.

## Preconditions

- branch from synchronized main containing commit
  `7d3497015e18300bd1625c2f143eebd796e9ac2f`;
- exact V4 implementation and authorization-issuer authorities remain present;
- the operational authorization and consumption files have already been copied
  into the evidence vault;
- the original transient operational files are removed before final package
  validation;
- the failed notebook remains renamed
  `ag-cu129-p3-p6-runtime-diag-failed-v4`;
- unchanged replay remains prohibited.

## Repository commands

```text
python -B -m auragateway.local_abc.p3_p6_runtime_diagnostic_failure_acceptance_v4 generate --repo-root <repo-root>
python -B -m auragateway.local_abc.p3_p6_runtime_diagnostic_failure_acceptance_v4 validate-evidence --repo-root <repo-root>
python -B -m auragateway.local_abc.p3_p6_runtime_diagnostic_failure_acceptance_v4 validate-package --repo-root <repo-root>
```

## Required validation

- exact policy identity;
- exact 25-file evidence receipt set;
- exact 25-member intake archive;
- exact 13-member runtime evidence archive;
- exact 12-member runtime manifest;
- authorization-to-consumption-to-lifecycle binding;
- saved-version, notebook, runtime-script, and log identities;
- P3-P5 pass state;
- P6 failure state;
- global and worker-specific request traces;
- teardown, cleanup, privacy, and action-budget boundaries;
- deterministic review and record bytes;
- absence of operational transient files.

## Failure handling

Do not regenerate runtime evidence, edit preserved evidence, or replay the
notebook. A validation failure means the repository package or evidence bytes
drifted. Restore the exact candidate or inspect the reported path.

## Next gate

After merge, design P3-P6 runtime diagnostic V5. Do not issue another runtime
authorization until the V5 harness, tests, evidence contract, and separate
authorization lifecycle are merged.
