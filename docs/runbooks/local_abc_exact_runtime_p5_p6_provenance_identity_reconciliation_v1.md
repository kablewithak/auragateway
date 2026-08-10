# Runbook: Exact-Runtime P5/P6 Provenance Identity Reconciliation V1

## Purpose

Use this gate after the provenance correction tranche is applied and before any
live P5/P6 execution authorization is issued.

The historical implementation generator is retained unchanged. Its original
`validate` command recomputes the historical review from current committed
documentation bytes and therefore detects the known pre-commit provenance
mismatch. After this reconciliation is merged, that command is not the
current-state pre-execution provenance gate.

The current-state gate is the dedicated reconciliation validator.

## Static reconciliation

Generate only the reconciliation record:

```text
python -m auragateway.local_abc.p5_p6_exact_runtime_provenance_identity_reconciliation_v1 generate --repo-root .
```

Validate exact committed evidence, retained historical generated artifacts, and
the semantic boundary of the runtime bytes embedded in the historical notebook:

```text
python -m auragateway.local_abc.p5_p6_exact_runtime_provenance_identity_reconciliation_v1 validate --repo-root .
```

This operation must not regenerate the P5/P6 implementation review, implementation
record, runtime script, wrapper, or notebook.

## Issuer revalidation

The corrected issuer binds the reconciliation source, tests, and record. Static
issuer validation must pass after the reconciliation record is generated:

```text
python -m auragateway.local_abc.p5_p6_exact_runtime_execution_authorization_v1 generate --repo-root .
python -m auragateway.local_abc.p5_p6_exact_runtime_execution_authorization_v1 validate-implementation --repo-root .
```

At live issuance, the operator confirmation and authorization payload bind the
exact reconciliation-record SHA-256. The issuer reruns the reconciliation
validator before authority can be created.

## Hard boundaries

- do not regenerate the historical P5/P6 runtime or notebook;
- do not edit the historical implementation review or record;
- do not alter the frozen authorization-design record;
- do not issue live authority during the reconciliation tranche;
- do not authorize pilot or final measured A/B/C execution.

## Required terminal state

```text
implementation_provenance_consistent=true
executable_runtime_identity_changed=false
live_authorization_issued=false
runtime_execution_authorized=false
p5_p6_exact_runtime_requalified=false
pilot_execution_authorized=false
final_measured_abc_execution_authorized=false
```

## Next gate

`REVALIDATE_EXACT_RUNTIME_P5_P6_EXECUTION_PRECONDITIONS_V1`
