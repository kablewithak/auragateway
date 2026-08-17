# AuraGateway B-vs-D Wrapper Zero-Exit Reporting Repair V1

## Defect

The governed B-vs-D runtime completed its diagnostic and returned process status
zero through `raise SystemExit(main())`.

The transaction-bound wrapper V1 caught `BaseException`, classified the normal
`SystemExit(0)` termination as `PRIMARY_FAILURE_CAPTURED`, persisted a wrapper
failure artifact, and re-raised the zero-exit exception into the notebook.

Disposition classification:

`CONTROL_PLANE_ZERO_EXIT_SYSTEMEXIT_FALSE_POSITIVE`

## Repair boundary

Historical V1 authorities remain immutable.

The repair introduces a versioned wrapper V2. V2 treats:

- `SystemExit(None)` as normal completion;
- integer `SystemExit(0)` as normal completion;
- non-zero `SystemExit` as a primary failure;
- other `BaseException` subclasses as primary failures.

The existing bounded secondary-failure reporting behavior remains intact.

## Regression proof

The local regression harness uses the same synthetic runtime payload against
both wrapper generations.

Baseline:

- V1 + `SystemExit(0)` -> primary-failure artifact + re-raised `SystemExit(0)`.

Intervention:

- V2 + `SystemExit(0)` -> normal completion, no primary-failure artifact.
- V2 + `SystemExit(None)` -> normal completion, no primary-failure artifact.
- V2 + `SystemExit(3)` -> primary failure retained and re-raised.
- V2 + `RuntimeError` -> primary failure retained and re-raised.

## Non-claims

This repair does not:

- alter or reinterpret the governed B-vs-D scientific result;
- alter the B-vs-D runtime payload;
- mutate the historical V1 wrapper;
- mutate the historical V1 authorization issuer;
- issue execution authorization;
- authorize unchanged replay;
- authorize another Kaggle execution;
- requalify P5 or P6;
- establish North-Star A/B/C effects.

## Successor boundary

Wrapper V2 must be bound by a separately reviewed successor authorization
issuer before any future governed execution can use it.
