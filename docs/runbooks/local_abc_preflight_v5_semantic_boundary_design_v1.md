# Runbook: Preflight V5 Semantic Boundary Design V1

## Purpose

Validate the V5 semantic/evidence architecture locally before building an
executable final offline verifier.

## Preconditions

- branch derives from accepted PR #224 merged main;
- repository is clean except the bounded design tranche;
- V4 semantic-channel reconciliation record remains present and valid.

## Validation

Run focused formatting, lint, compile, mypy and pytest.

Generate the deterministic design record:

`python -m auragateway.local_abc.preflight_v5_semantic_boundary_design_v1 generate --repo-root .`

Validate it:

`python -m auragateway.local_abc.preflight_v5_semantic_boundary_design_v1 validate-generated --repo-root .`

Validate the complete design tranche:

`python -m auragateway.local_abc.preflight_v5_semantic_boundary_design_v1 validate-implementation --repo-root .`

## Safety boundary

No Kaggle execution.
No execution authorization.
No package installation.
No model load.
No worker startup.
No model request.

## Next gate

implement_final_offline_verifier_v5_from_accepted_semantic_boundary
