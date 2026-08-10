# Runbook: Exact-Runtime P5/P6 Execution Authorization Issuer V1

## Static implementation phase

The issuer PR may generate and validate only:

- issuer architecture review;
- issuer implementation record.

It must not create the live authorization or terminal receipt and must not start
Kaggle, runtime, model, or worker execution.

Static commands:

```text
python -m auragateway.local_abc.p5_p6_exact_runtime_execution_authorization_v1 generate --repo-root .
python -m auragateway.local_abc.p5_p6_exact_runtime_execution_authorization_v1 validate-implementation --repo-root .
```

## Post-merge issuance preconditions

After the issuer is merged and cleanup is complete:

1. synchronize clean `main` with `origin/main`;
2. record the exact issuer merge commit;
3. revalidate the static issuer implementation;
4. revalidate the bound P5/P6 implementation and semantic boundary;
5. observe Kaggle notebook settings freshly;
6. confirm T4 x2, two allocated GPUs, Internet OFF, no credentials, no customer
   data, and no external network access;
7. create canonical `IssuanceConfirmation` JSON outside the repository;
8. ensure both platform observation and operator confirmation are no more than
   15 minutes old at issuance;
9. issue once.

The exact operator phrase is:

```text
I_CONFIRM_FRESH_KAGGLE_T4_X2_INTERNET_OFF_AND_AUTHORIZE_ONE_EXACT_RUNTIME_P5_P6_REQUALIFICATION_V1_EXECUTION
```

The maximum authorization lifetime is 240 minutes; the default is 180 minutes.

## Confirmation validation

```text
python -m auragateway.local_abc.p5_p6_exact_runtime_execution_authorization_v1 validate-confirmation --confirmation-json <path>
```

## Live lifecycle

Issue once:

```text
python -m auragateway.local_abc.p5_p6_exact_runtime_execution_authorization_v1 issue --repo-root . --confirmation-json <path>
```

The local authorization artifact must be transferred to the governed Kaggle
input with the filename `execution_authorization_v1.json` without changing its
bytes.

Validate immediately before execution:

```text
python -m auragateway.local_abc.p5_p6_exact_runtime_execution_authorization_v1 validate-live --repo-root .
```

After a known execution attempt, terminalize with `CONSUMED` and the appropriate
known outcome. PASS, FAIL, AMBIGUOUS, and DIAGNOSTIC_INVALID require a saved
version id and evidence ZIP SHA-256.

If the attempt result cannot be established, use `OUTCOME_UNKNOWN`. If execution
never starts, use `CANCELLED_UNUSED`, `ABANDONED_BEFORE_EXECUTION`, or, after the
window has elapsed, `EXPIRED_UNUSED`.

```text
python -m auragateway.local_abc.p5_p6_exact_runtime_execution_authorization_v1 terminalize --repo-root . --disposition <DISPOSITION> [--outcome <OUTCOME>] [--saved-version-id <ID>] [--evidence-zip-sha256 <SHA>] [--terminal-log-sha256 <SHA>]
```

## Hard boundaries

- never overwrite a live authorization;
- never overwrite a terminal receipt;
- never reuse terminal authority;
- no hidden retry or replacement worker;
- no pilot authority;
- no final measured A/B/C authority.

## Static tranche terminal state

```text
authorization_issuer_implemented=true
live_authorization_issued=false
runtime_execution_authorized=false
p5_p6_exact_runtime_requalified=false
pilot_execution_authorized=false
final_measured_abc_execution_authorized=false
```
