# Runbook: P5/P6 Mechanism-Admission Successor Implementation V1

## Safety boundary

Repository-only implementation. Do not start workers, install the governed GPU runtime, execute Kaggle, perform model requests, or issue execution authorization.

## Authored paths

- `src/auragateway/local_abc/p5_p6_mechanism_admission_successor_v1.py`
- `src/auragateway/local_abc/templates/p5_p6_mechanism_admission_successor_v1.py.tmpl`
- `tests/unit/local_abc/test_p5_p6_mechanism_admission_successor_v1.py`
- `docs/adr/2026-08-22-local-abc-p5-p6-mechanism-admission-successor-runtime-outcome-contract-addendum-v1.md`
- `docs/reports/AuraGateway_P5_P6_Mechanism_Admission_Successor_Implementation_V1.md`
- `docs/runbooks/local_abc_p5_p6_mechanism_admission_successor_implementation_v1.md`

## Producer-owned generated paths

- `benchmarks/local_abc/auragateway_p5_p6_mechanism_admission_successor_v1_implementation_review.json`
- `benchmarks/local_abc/auragateway_p5_p6_mechanism_admission_successor_v1_implementation_record.json`
- `notebooks/auragateway_p5_p6_mechanism_admission_successor_v1.ipynb`

Do not edit generated files manually.

## Normal path

1. Install all six authored files as complete files.
2. Run syntax/format/lint/type validation on authored Python files.
3. Run the producer with `--write` once final authored bytes are stable.
4. Run the producer with `--check`.
5. Run focused pytest.
6. Run final Ruff lint/format, mypy, and `git diff --check`.
7. Inspect the exact implementation diff.
8. Stage only the bounded successor implementation paths.
9. Verify staged bytes, commit, push, open PR, inspect, merge, and sync main.

Keep routine successful checks consolidated. If any material validation fails, stop and use the project's pre-remediation circuit before mutation.

## Required static proofs

- exact V2 source/template/test authority identities;
- exact Gate B contract/assessment identities;
- exact successor design/review identities;
- exact implementation-addendum identity;
- semantic state inventory;
- `finish_reason == "stop"` remains blocking;
- response-content digest survives semantic negatives;
- V2/successor `decide_p5()` AST identity;
- V2/successor `decide_p6()` AST identity;
- canonical process success token is `PASSED` at the target-environment creation consumer;
- V2 authorization scope is not reusable;
- generated notebook contains no execution state.

## Next gate after merge

`DESIGN_AND_MERGE_P5_P6_MECHANISM_ADMISSION_SUCCESSOR_V1_EXECUTION_AUTHORIZATION_ISSUER`
