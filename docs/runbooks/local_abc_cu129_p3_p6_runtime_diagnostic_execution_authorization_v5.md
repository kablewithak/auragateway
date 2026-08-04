# Runbook: P3-P6 Runtime Diagnostic Execution Authorization V5

## Purpose

Operate the V5 issuer without conflating repository implementation, live
authorization issuance, Kaggle execution, or authorization consumption.

## Repository implementation validation

Run only on synchronized clean `main` with both transient paths absent:

```powershell
python -m auragateway.local_abc.full_abc_local_environment_qualification_cu129_p3_p6_runtime_diagnostic_execution_authorization_v5 validate-implementation --repo-root .
```

This validates the issuer and exact V5 identities. It does not issue authority.

## Issuance preconditions

Before issuing:

1. confirm local `main` equals `origin/main`;
2. confirm the issuer implementation commit is merged;
3. confirm authorization and consumption paths are absent and untracked;
4. confirm the exact notebook, runtime-script, wrapper, model, and backend
   identities;
5. confirm one bounded execution is immediately ready to start.

## Issuance boundary

Issue only with explicit `--operator-confirm` and exact identity arguments.
The authorization window must not exceed 240 minutes.

The created authorization file must remain untracked. Do not commit, push,
attach, or copy it into a permanent repository artifact.

## Verification boundary

Immediately before execution, run the issuer `verify` command. Stop when the
authorization is expired, consumed, non-canonical, identity-drifted, tracked,
or outside synchronized clean `main`.

## Consumption boundary

After the single passed, failed, or interrupted Kaggle attempt, create exactly
one consumption receipt using explicit operator confirmation and the saved
version identifier.

A consumed authorization is never reusable. An unchanged replay requires a new
reviewed implementation and a fresh authorization lifecycle.

## Prohibited actions

- do not issue during repository generation or validation;
- do not execute Kaggle before live issuance and verification;
- do not permit external network access or credentials;
- do not log raw prompts, raw outputs, or customer data;
- do not exceed one session, three model loads, three worker starts, five model
  requests, or 32 output tokens per request;
- do not run measured A/B/C trajectories;
- do not track transient authorization or consumption files.
