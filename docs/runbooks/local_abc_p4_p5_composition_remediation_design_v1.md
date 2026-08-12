# P4/P5 Composition Remediation Design V1 Runbook

## Purpose

Validate the design-only P4/P5 composition remediation contract.

This tranche does not modify the accepted predecessor runtime, generate a
successor runtime, authorize execution, or execute Kaggle.

## Frozen intervention

Change only the instruction tail of both synthetic cache-context constants from
the historical V5 wording to the accepted V4 wording.

Do not remove the assistant acknowledgement or change the four-role composition.

## Authority checks

Validation must prove exact identities for:

1. historical P4 execution acceptance;
2. historical P4 implementation record;
3. historical P4 V4/V5 template matrix;
4. current P5/P6 predecessor runtime;
5. current C3 failure reconciliation;
6. controlled P4/P5 differential design;
7. controlled P4/P5 differential implementation;
8. accepted differential terminalization reconciliation.

The authority validator must fail closed on byte drift.

## Validation sequence

Run:

1. Ruff format on the candidate-owned design source and focused test;
2. Ruff check on the candidate-owned design source and focused test;
3. focused mypy on the candidate-owned Python;
4. deterministic design generation;
5. deterministic design validation;
6. focused pytest;
7. complete repository pytest;
8. deterministic design validation again;
9. trailing-whitespace checks on authored mutable text only;
10. exact candidate-path validation.

Do not run `ruff check .` as the release gate.

Do not apply whitespace cleanup to evidence-vault artifacts.

## Required design assertions

The generated design record must freeze:

- exact two-tail V5-to-V4 intervention;
- unchanged `system,user,assistant,user` message roles;
- unchanged synthetic assistant acknowledgement;
- unchanged long cache bodies and 24x repetition count;
- unchanged prefix A/B semantics;
- unchanged generation controls;
- unchanged P5 and P6 decision semantics;
- durable pre-request token-identity evidence;
- full P5/P6 trajectory as the future remediation acceptance gate;
- no current execution authority.

## Failure rule

If an accepted authority, intervention precondition, invariant, deterministic
record identity, or safety field fails validation, stop.

Do not broaden the remediation to another variable merely to make validation
pass.

No Case C or GPU execution is authorized by this design.

## Next gate after merge

`IMPLEMENT_AND_MERGE_P4_P5_COMPOSITION_REMEDIATION_V1`
