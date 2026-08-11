# P4/P5 Composition Differential Execution Authorization V1 Runbook

## Current state

The issuer is static until merged.

Do not run `authorize-generate` from this feature branch.

Do not run Kaggle from this tranche.

## Static validation

Use the repository Python environment to run:

`python -m auragateway.local_abc.p4_p5_composition_differential_execution_authorization_v1 validate --repo-root .`

Static validation requires:

- merged design ancestry;
- exact design-record identity;
- exact implementation authority identities;
- exact generated review and record;
- no live authorization;
- no live transaction manifest;
- no terminal receipt.

## Live command 1

Only after the issuer has been merged, local `main` equals `origin/main`, and
the repository is clean:

`python -m auragateway.local_abc.p4_p5_composition_differential_execution_authorization_v1 authorize-generate --repo-root .`

The command prints a dynamic SHA-256 challenge.

The operator must retype that exact challenge interactively.

The command then writes the transaction-bound notebook to the Desktop and
creates the local live lifecycle records.

No authorization-specific Kaggle input is created.

## Platform gate

After artifact generation and before Save & Run All:

- verify Kaggle accelerator is T4 x2;
- verify two GPUs are allocated;
- verify Internet is Off;
- perform exactly one Save & Run All.

Do not repeat Save & Run All for the same transaction.

A second observed execution invalidates governed acceptance.

## Live command 2

After the transaction reaches a terminal state, terminalize it with the exact
saved version and platform-observation timestamp.

Attempted execution uses `CONSUMED` with an explicit outcome or
`OUTCOME_UNKNOWN` without an outcome.

Unused authority uses one of:

- `EXPIRED_UNUSED`
- `CANCELLED_UNUSED`
- `ABANDONED_BEFORE_EXECUTION`

The terminal receipt is non-overwriting and authority is never reusable.

## Evidence

Expected governed evidence ZIP:

`ag-p4-p5-composition-differential-evidence-v1.zip`

A missing evidence ZIP does not prevent terminalization.

Raw prompts and raw model outputs remain prohibited from persisted evidence.

## Post-terminal gate

Preserve the live authorization, manifest, terminal receipt, saved-version
identity, terminal log, evidence ZIP when present, and metadata-safe result
artifacts before clearing transient operational lifecycle files.
