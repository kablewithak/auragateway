# AuraGateway Transaction-Bound P5/P6 Runtime Integration V1

## Purpose

Bind the exact-runtime P5/P6 behavioral payload to the merged transaction-bound
authorization boundary without reintroducing authorization-specific Kaggle
transport.

## Predecessor evidence

Saved version `341548056` remains governed `OUTCOME_UNKNOWN`. Its accepted
governance establishes diagnostic masking and requires a symbolic-link
regression case, while explicitly leaving the earliest pre-cleanup exception
unrecovered.

Static V2 inspection additionally identifies a successor-only harness defect:
the bounded-process helper labels a zero return code `PASSED`, while
`install_runtime()` requires `ZERO_EXIT`. This tranche fixes that inconsistency
but does not claim it was the unrecovered primary exception in the failed run.

## Successor boundary

The runtime payload is deterministically generated from the immutable V2
template. Authorization transport functions and authorization-specific Kaggle
input discovery are removed. The outer transaction-bound executable wrapper
owns authorization admission and injects only the transaction identity into the
runtime payload.

The six-request P5/P6 contract remains:

1. BASE_COLD
2. BASE_WARM
3. NEGATIVE_PREFIX
4. POST_RESET_COLD
5. CROSS_WORKER_COLD
6. WORKER1_RETENTION

## Harness remediations

- Successful bounded subprocess outcome is `ZERO_EXIT`.
- Scratch/venv snapshots count symbolic links instead of rejecting them.
- Durable input hashing remains strict and continues rejecting symlinks.
- Scratch-cleanup snapshot failures are secondary and cleanup still attempts.
- Worker teardown failures are converted to secondary reports.
- Evidence packaging failures preserve an already-written primary failure and
  cannot replace it as the terminal cause.

## Safety

This implementation does not issue live authority, does not run Kaggle, does
not establish current-runtime P5/P6 qualification, and does not establish
runtime anti-replay.

## Next gate

`CPU_OR_MANUAL_KAGGLE_TOPOLOGY_REHEARSAL_V1`
