# Runbook: Measured A/B/C Execution Authorization V1

This runbook is local-first and execution-safe. Implementation validation does not issue
authorization and does not run Kaggle.

## Generate deterministic implementation evidence

```powershell
python -m `
    auragateway.local_abc.measured_abc_execution_authorization_v1 `
    generate `
    --repo-root .
```

## Validate implementation

```powershell
python -m `
    auragateway.local_abc.measured_abc_execution_authorization_v1 `
    validate-implementation `
    --repo-root .
```

Before the readiness record exists, the valid expected state is:

```text
implementation_status=IMPLEMENTED_NOT_ISSUED
issuance_ready=false
authorization_issued=false
runtime_execution_authorized=false
measured_abc_execution_authorized=false
next_gate=resolve_measured_abc_execution_readiness_v1
```

## Issuance boundary

Do not run `issue` merely because the module is merged.

Issuance requires:

1. committed and valid measured A/B/C readiness record;
2. main equals origin/main;
3. clean working tree;
4. fresh Kaggle settings observation;
5. explicit operator confirmation;
6. exact readiness SHA-256;
7. exact frozen execution-manifest SHA-256;
8. exact runtime and budget confirmation.

The issued authorization stores the SHA-256 of the exact operator-confirmation file.

## Active-authority worktree

After issuance, `verify`, `consume`, and `abandon` require the repository to remain on the
issued main commit and the working tree to contain exactly one untracked file: the authorization
artifact. This prevents local source/config drift from being hidden behind a still-valid token.

## Terminal lifecycle

A used authority must be consumed with one outcome:

- PASSED
- FAILED
- INTERRUPTED
- TIMED_OUT
- KAGGLE_PLATFORM_TERMINATED
- OUTCOME_UNKNOWN

A PASSED consumption additionally requires saved-version ID, evidence-bundle SHA-256, and
terminal-log SHA-256.

An unused authority must be abandoned rather than deleted.

## Safety

Never reuse the historical 72-trajectory authorization. Never treat the historical Groq
execution manifest as current authority. Never create readiness evidence from inside the issuer.
