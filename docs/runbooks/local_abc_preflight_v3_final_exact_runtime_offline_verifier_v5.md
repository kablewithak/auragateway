# Runbook: Final Offline Verifier V5 Implementation

## Purpose

Validate the repository implementation of Final Offline Verifier V5 before any
execution authorization exists.

## Preconditions

- current branch derives from the accepted V5 semantic-boundary merge;
- the accepted V5 semantic-boundary design record is unchanged;
- V4 saved version 341211001 remains preserved diagnostic evidence;
- no live verifier authorization exists;
- no Kaggle execution is performed during this tranche.

## Focused validation

Run formatter before lint for the Python source and test.

Run:

`python -m py_compile <source> <test>`

`python -m mypy <source> <test>`

`python -m pytest <test>`

Generate the deterministic implementation artifacts:

`python -m auragateway.local_abc.preflight_v3_exact_runtime_offline_compatibility_v5 generate --repo-root .`

Validate the generated artifacts:

`python -m auragateway.local_abc.preflight_v3_exact_runtime_offline_compatibility_v5 validate-generated --repo-root .`

Validate the notebook boundary:

`python -m auragateway.local_abc.preflight_v3_exact_runtime_offline_compatibility_v5 validate-notebook --repo-root .`

Validate the accepted design authority:

`python -m auragateway.local_abc.preflight_v3_exact_runtime_offline_compatibility_v5 validate-design-authority --repo-root .`

After generation, validate the complete implementation:

`python -m auragateway.local_abc.preflight_v3_exact_runtime_offline_compatibility_v5 validate-implementation --repo-root .`

## Required semantic gates

semantic_decisions_reading_stdout_excerpt=0
semantic_decisions_reading_stderr_excerpt=0
lossy_transformations_before_semantic_decision=0
truncation_before_semantic_decision=0
statically_predictable_successor_failures=0

## Safety boundary

No Kaggle execution.
No execution authorization.
No model load.
No worker startup.
No model request.
No P5/P6 execution.
No pilot.
No measured A/B/C.

## Next gate

implement_single_use_final_offline_verifier_v5_execution_authorization
