# P4/P5 Composition Differential Design V1 Runbook

## Purpose

Validate the deterministic design-only P4/P5 composition differential.

This tranche does not execute the differential and does not issue runtime
authority.

## Frozen experiment

Case A:

`system -> final JSON object`

Case B:

`system -> synthetic cache context -> assistant acknowledgement -> final JSON object`

The current P5/P6 final canonical object is identical between A and B.

The fixed request order is:

`A, B, B, A, A, B`

The treatment variable is:

`MESSAGE_COMPOSITION_ONLY`

## Validation sequence

Run:

1. Ruff format on the candidate-owned design source and focused tests;
2. Ruff lint on the candidate-owned design source and focused tests;
3. focused mypy;
4. deterministic design generation;
5. deterministic design validation;
6. focused pytest;
7. complete repository pytest;
8. deterministic design validation again;
9. authored-document trailing-whitespace validation;
10. exact candidate-path validation.

Do not use repository-wide Ruff as a release gate unless its baseline has first
been established clean or the tranche explicitly owns repository lint
remediation.

## Frozen identity

Design record SHA-256:

`5bcea57f47573712c5776fcd7d210584c96ece5cf86d09902cf29453e27e39d1`

Any deterministic regeneration that changes this identity before an intentional
design change must be investigated before staging.

## Safety

Required state:

- `runtime_execution_authorized=false`
- `new_execution_authorized=false`
- `kaggle_execution_performed=false`
- `gpu_execution_performed=false`
- `model_loaded=false`
- `worker_started=false`
- `model_requests_performed=0`
- `runtime_fix_authorized=false`
- `measured_abc_execution_authorized=false`

No human authorization challenge exists in this tranche.

Do not construct one manually.

## Failure rule

If an accepted authority identity, case shape, generation control, deterministic
record identity, or safety state fails validation, stop.

Do not weaken the validator to accommodate drift.

Do not execute Kaggle.

Do not add Case C unless a future governed A/B execution is nondiscriminating
and a separate design tranche authorizes that extension.

## Next gate after merge

`IMPLEMENT_AND_MERGE_P4_P5_COMPOSITION_DIFFERENTIAL_V1`
