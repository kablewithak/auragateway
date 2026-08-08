# Runbook: Measured A/B/C Variance Pilot V1

This slice is local-first and non-executing.

## Generate deterministic pilot assets

```powershell
python -m `
    auragateway.local_abc.measured_abc_variance_pilot_v1 `
    generate `
    --repo-root .
```

Expected:

```text
pilot_case_count=6
pilot_trajectory_count=54
pilot_turn_count=216
maximum_request_attempt_count=432
pilot_execution_authorized=false
final_measured_abc_execution_authorized=false
```

## Validate implementation

```powershell
python -m `
    auragateway.local_abc.measured_abc_variance_pilot_v1 `
    validate-implementation `
    --repo-root .
```

## Authorization

Do not run `issue` until the pilot runtime launcher and its committed readiness record have
been merged. The issuer enforces this boundary.

After launcher readiness exists, issuance still requires synchronized clean main, a fresh
Kaggle capability observation, exact pilot manifest/schedule identities, and explicit operator
confirmation.

Pilot authorization is separate from final measured A/B/C authorization.

## Future execution

The future launcher must consume the committed pilot manifest and schedule exactly. It must not
regenerate case selection or reorder trajectories.

## Terminalization

A used pilot authority must be consumed. An unused one must be abandoned. Deleting the
authorization file is not a valid lifecycle transition.

## Privacy

Do not publish raw prompts, user messages, retrieved documents, model outputs, worker logs,
credentials, secrets, or customer data.
