# Runbook: Exact-Runtime P5/P6 Execution Authorization Design V1

## Purpose

Validate and publish the design contract for a future one-use P5/P6 execution
authorization issuer. This runbook does not issue authority.

## Preconditions

- branch starts from synchronized clean `main`
- base main is `9cc06c02c372fa2e7637c432759e7a1d4db56e9e`
- merged P5/P6 implementation remains byte-identical
- accepted V5 capability record remains byte-identical
- no runtime execution occurs during this tranche

## Local validation order

1. Apply the six design files.
2. Run Ruff fix and formatting on changed mutable Python.
3. Run clean Ruff lint and format checks.
4. Run focused mypy on source and tests.
5. Generate the deterministic design JSON.
6. Validate deterministic design JSON.
7. Run focused pytest.
8. Run repository pytest and baseline-aware repository mypy.
9. Stage exact paths only.
10. Prove staged whitespace and path set.
11. Commit, push, manually merge, synchronize `main`, prove ancestry, and clean
    local/remote feature refs.

## Hard boundary

The design tranche must end with:

```text
live_authorization_issued=false
runtime_execution_authorized=false
p5_p6_exact_runtime_requalified=false
pilot_execution_authorized=false
final_measured_abc_execution_authorized=false
```

## Next gate

`IMPLEMENT_EXACT_RUNTIME_P5_P6_EXECUTION_AUTHORIZATION_V1_ISSUER`
