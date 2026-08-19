# Local ABC — Canonical Synthetic Prefix C4 Single-Use Execution Authorization V1

Status: `IMPLEMENTED_NOT_ISSUED`

## Purpose

Operate the merged single-use authorization issuer for
`CANONICAL_SYNTHETIC_PREFIX_C4_BEHAVIORAL_QUALIFICATION_V1`.

The static implementation tranche must only use `generate` and `validate`.
Do not run `authorize-generate` before the issuer is merged and the repository has
been synchronized back to clean `main`.

## Static Validation

The issuer must verify byte-identical:

- frozen authorization-design record;
- C4 implementation review and record;
- C4 qualification request;
- reusable-prefix identity receipt;
- C4 successor runtime.

Static validation must fail if any live authorization, live manifest, platform
receipt, or terminal receipt already exists.

## Live Issuance Preconditions

After issuer merge:

1. synchronize local `main` exactly to `origin/main`;
2. require a clean worktree and index;
3. verify the authorization-design merge is an ancestor;
4. derive the issuer merge commit from first-parent history;
5. verify issuer source/template/review/record did not drift after that merge;
6. require no prior live lifecycle artifacts;
7. require the intended output notebook path not to exist.

## Fresh Human Ceremony

Run `authorize-generate`.

The issuer prints a fresh dynamic SHA-256 challenge. The human operator must
manually retype that exact 64-character challenge.

Do not ask ChatGPT, another model, the runtime, or another script to reproduce the
challenge.

A mismatch or confirmation older than 15 minutes aborts issuance.

## Governed Notebook

The generated notebook name is:

`ag-c4-canonical-prefix-qual-v1`

The notebook contains one transaction-bound wrapper code cell and embeds:

- canonical authorization bytes;
- exact frozen C4 runtime bytes;
- transaction ID;
- issuer merge commit;
- issuer source SHA-256;
- runtime SHA-256;
- wrapper-generator contract SHA-256.

No authorization-specific Kaggle input or manual confirmation JSON is used.

## Platform Observation

After the notebook artifact exists, inspect Kaggle Notebook Settings and confirm:

- accelerator: T4 x2;
- two allocated GPUs;
- Internet: Off.

Persist the durable observation with `record-platform-observation` before the one
Save & Run All.

The receipt is control-plane evidence only and is not mounted into the runtime.

## Execution

Perform exactly one Save & Run All.

Do not retry the notebook under the same authority if the run fails, stalls, or
the UI is ambiguous. The authority is single-use.

The runtime itself allows at most:

- one runtime installation attempt;
- one import-closure probe;
- three model loads;
- three worker starts;
- three model requests;
- three teardowns;
- zero hidden retries;
- zero replacement requests;
- zero external network requests.

## Wrapper Admission

The wrapper validates authorization and runtime identities before executing the
bound payload. It checks the live time window and machine-observed two-GPU
topology.

The wrapper passes `AURAGATEWAY_TRANSACTION_ID` to the runtime.

A clean `SystemExit(0)` from the runtime is treated as successful notebook
completion. A nonzero `SystemExit` or another exception remains a primary failure.

## Terminalization

After the one execution attempt, terminalize once.

For a completed run use disposition `CONSUMED` and record the observed C4 state:

- `QUALIFIED`
- `NOT_QUALIFIED`
- `INVALID_EXECUTION`

For an execution whose final state cannot be responsibly determined, use
`OUTCOME_UNKNOWN` rather than guessing.

Unused authorities may terminate as:

- `EXPIRED_UNUSED`
- `CANCELLED_UNUSED`
- `ABANDONED_BEFORE_EXECUTION`

A `QUALIFIED` observation requires saved-version ID, platform receipt, and evidence
ZIP SHA-256.

## Acceptance Boundary

Terminalization does not accept C4 into repository state.

Preserve the lifecycle artifacts and execution evidence. A separate reconciliation
must verify the saved version, platform budget, authorization consumption, runtime
identity, evidence identities, and C4 decision before any P5/P6 successor work.

## Non-Claims

Do not claim C4 qualification, P5/P6 requalification, final A/B/C effects,
prefix-cache correctness, historical root cause, or production readiness from
issuer implementation or runtime observation alone.
