# Local ABC P4/P5 Composition Remediation Implementation V1

## Purpose

Generate and statically validate the remediation successor without executing
Kaggle or issuing runtime authority.

## Owned implementation surface

The implementation tranche owns seven repository artifacts: the deterministic
producer, generated successor runtime, focused tests, deterministic review,
deterministic record, this runbook and the implementation report.

The accepted predecessor runtime is immutable input authority.

## Required local validation order

1. Ruff format candidate-owned mutable Python.
2. Ruff check candidate-owned mutable Python.
3. mypy candidate-owned Python.
4. Deterministic `generate`.
5. Deterministic `validate`.
6. Ruff format/check and mypy on the generated successor runtime.
7. Focused pytest.
8. Full repository pytest.
9. Authored mutable-text diff check and exact candidate boundary.

## Runtime non-authority

Generation and validation are static operations. They do not authorize a
Kaggle session, model load, worker start or model request.

## Eventual confirmation

After this implementation is merged, execution authorization must be designed
and merged separately. That future authority must include the durable platform
observation control frozen by the remediation design before Save & Run All.

The governed confirmation must use the full remediated P5/P6 qualification
trajectory, not an isolated A/R diagnostic.
