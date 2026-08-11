# Local ABC Transaction-Bound P5/P6 Runtime Integration V1

This tranche is static implementation only.

## Generate

Run the integration generator from the repository root. It derives the
successor runtime payload from the immutable V2 template and writes:

- `src/auragateway/local_abc/p5_p6_transaction_bound_runtime_v1.py`
- `benchmarks/local_abc/auragateway_transaction_bound_p5_p6_runtime_integration_v1_review.json`
- `benchmarks/local_abc/auragateway_transaction_bound_p5_p6_runtime_integration_v1.json`

## Validate

Validate the generated artifacts, then run Ruff, mypy, focused pytest, and
repository regression gates.

Do not hand-edit the generated runtime payload or generated JSON records.
Change the integration generator and regenerate.

## Execution control

No live authorization is issued by this tranche. No GPU execution is
authorized. After merge, perform the CPU/manual Kaggle topology rehearsal
before any `authorize-generate` transaction.

## Next gate

`CPU_OR_MANUAL_KAGGLE_TOPOLOGY_REHEARSAL_V1`
