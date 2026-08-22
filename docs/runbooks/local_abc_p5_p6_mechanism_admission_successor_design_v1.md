# Runbook: P5/P6 Mechanism-Admission Successor Design V1

## Purpose

Generate and validate the repository-only successor design that separates semantic observation from mechanism admission while preserving Exact-Runtime P5/P6 Requalification V2 as immutable predecessor evidence.

## Safety boundary

This runbook performs no model request, GPU execution, Kaggle execution, runtime installation, worker startup, or authorization issuance.

Expected scientific state after this tranche:

- C4-S: `NOT_QUALIFIED`
- C4-M: `QUALIFIED`
- P5: not requalified
- P6: not requalified
- new execution authorization: false

## Preconditions

- Current branch is the bounded successor-design feature branch.
- Base commit is `f534a27d3e07fc699c7fb1e4e257730cc71590f4`.
- Index contains no unrelated staged paths.
- The four preserved paragraph-order lifecycle artifacts remain untouched.
- Exact-Runtime P5/P6 Requalification V2 predecessor identities match the design producer.
- C4 mechanism-admission contract and assessment identities match the design producer.

## Authored paths

- `src/auragateway/local_abc/p5_p6_mechanism_admission_successor_design_v1.py`
- `tests/unit/local_abc/test_p5_p6_mechanism_admission_successor_design_v1.py`
- `docs/adr/2026-08-22-local-abc-p5-p6-mechanism-admission-successor-design-v1.md`
- `docs/reports/AuraGateway_P5_P6_Mechanism_Admission_Successor_Design_V1.md`
- `docs/runbooks/local_abc_p5_p6_mechanism_admission_successor_design_v1.md`

## Generated paths

- `benchmarks/local_abc/auragateway_p5_p6_mechanism_admission_successor_design_v1.json`
- `benchmarks/local_abc/auragateway_p5_p6_mechanism_admission_successor_design_v1_review.json`

Generated files are producer-owned. Do not edit them manually.

## Generation

Run the design producer with `--write` only after all five authored files are installed as complete files.

The producer must validate predecessor and Gate B authorities before writing outputs.

## Deterministic check

Run the producer with `--check` after generation. Any byte drift between a fresh rebuild and repository outputs is a failure.

## Validation order

Use separate validation blocks in this order:

1. producer generation;
2. producer deterministic check;
3. focused pytest;
4. Ruff lint;
5. Ruff format check;
6. focused mypy;
7. `git diff --check`;
8. inspect exact changed paths and diff.

Do not stage during validation.

## Failure handling

At the first material failure, stop. Run a pre-remediation inspection before changing files. Classify recurrence and identify downstream effects before the remediation.

For a Python remediation, consider formatting, line length, lint, typing, tests, and generated review hashes before changing the file. Regenerate only producer-owned dependents whose inputs actually changed.

## Acceptance

The design tranche is acceptable only if:

- predecessor V2 identity is valid;
- Gate B mechanism-admission authority is valid;
- semantic equality and JSON validity are explicitly non-blocking for mechanism admission;
- transport/envelope/identity/metric/worker/lifecycle failures remain blocking;
- P5 criteria are not relaxed;
- P6 criteria are not relaxed;
- V2 authorization reuse is prohibited;
- generated outputs reproduce deterministically;
- no execution authority is created.

## Next gate

`IMPLEMENT_AND_MERGE_P5_P6_MECHANISM_ADMISSION_SUCCESSOR_V1`
