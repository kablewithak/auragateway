# ADR: Preserve Exact-Runtime P5/P6 V2 Saved Version 341548056 as Outcome-Unknown Diagnostic Evidence

**Date:** 2026-08-10
**Status:** Proposed governance acceptance
**Base main:** `0ee9e5b8fe8fb8fbf5268f2c270748e1a4c9b8e2`

## Context

Exact-Runtime P5/P6 Requalification V2 executed once on Kaggle as saved version
`341548056`. The run crossed the V1 authorization-discovery failure
boundary and verified the expected V2 runtime-source identity.

The Kaggle execution terminated with:

`RuntimeError: target runtime contains a symbolic link`

The externally visible traceback is in `cleanup_scratch()` ->
`directory_snapshot()`.

Kaggle preserved a partial results archive, but the run did not produce the
governed evidence ZIP named by the authorization. It also did not produce the
normal summary, failure report, bundle manifest, or scratch-cleanup report.

The single-use authorization has therefore been terminalized as
`OUTCOME_UNKNOWN`, not `FAILED`, because the governed terminal-evidence contract
did not complete.

## Decision

Preserve saved version `341548056` as an accepted diagnostic
`OUTCOME_UNKNOWN` transaction.

Classify the supported failure domain as:

`HARNESS_SEMANTIC_FAILURE`

Record separately that diagnostic masking is established. The visible cleanup
exception must not be promoted into proof of the earliest pre-cleanup exception.

Preserve byte-for-byte:

- the issued V2 authorization;
- the terminal OUTCOME_UNKNOWN receipt;
- the Kaggle terminal log;
- the raw partial Kaggle results ZIP;
- the exact raw partial-results ZIP, with its member inventory validated in-place.

The acceptance must not fabricate the missing governed evidence ZIP.

## Supported claims

- V2 crossed the prior V1 authorization-discovery failure boundary.
- Runtime-source identity verification passed.
- The governed terminal evidence path did not complete.
- P5 was not run.
- P6 was not run and remained `P6_NOT_STARTED`.
- Zero model requests were performed.
- The V2 authorization is terminal and non-reusable.
- The visible terminal exception is harness-side snapshot/cleanup behavior.
- Diagnostic masking is established.

## Non-claims

This acceptance does not establish:

- the exact first pre-cleanup exception;
- that runtime installation never began;
- model incompatibility;
- P5 failure;
- P6 failure;
- current-runtime incompatibility;
- runtime anti-replay;
- authority for another Kaggle execution.

Accepted V5 exact-runtime offline capability remains intact.

## Architecture consequence

Do not remediate the symbolic-link condition yet.

The next tranche must reconcile execution authorization architecture before any
successor implementation. The selected design direction is Option 3:
a transaction-bound authorized execution artifact with no separately mounted
authorization-specific Kaggle input.

That direction is not repository-frozen by this governance ADR. It must be
decided in the next dedicated architecture ADR.

## Next gate

`DESIGN_AND_MERGE_TRANSACTION_BOUND_EXECUTION_AUTHORIZATION_ARCHITECTURE_V1`
