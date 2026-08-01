# Runbook: P3-P6 Runtime Diagnostic Execution Authorization V2

## Preconditions

- branch `main`;
- local `HEAD` equals `origin/main`;
- merged main contains `87f2d4e08043c0c6ec5dee93d14c0523f531e8fe`;
- implementation feature `d6837f057790279727fbb71177a615a0a12928ef` is an ancestor;
- repository is clean except for the permitted transient V2 authorization lifecycle files;
- V2 authorization and consumption paths are untracked;
- notebook SHA-256 is `912b1888d110a0996122e57dfb8992748f6c0d531472b05339eca64ad43debdd`;
- model snapshot SHA-256 is `84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94`;
- backend is `TRITON_ATTN`;
- Kaggle Internet is disabled and accelerator is T4 x2.

## Lifecycle commands

Use the module:

```text
auragateway.local_abc.full_abc_local_environment_qualification_cu129_p3_p6_runtime_diagnostic_execution_authorization_v2
```

Commands:

```text
generate
validate-implementation
issue
verify
consume
```

Issuance requires explicit confirmation of scope, notebook identity, model identity, backend and validity window. Consumption requires explicit confirmation, terminal outcome and positive Kaggle saved-version ID.

## Fail-closed rules

- never overwrite an existing authorization or receipt;
- never track either transient file;
- do not issue from a feature branch or unsynchronized main;
- do not execute after expiry or after a consumption receipt exists;
- do not replay an unchanged PASSED, FAILED or INTERRUPTED attempt;
- do not claim the V1 root cause from the V2 path correction alone;
- preserve the V2 runtime installation report and bounded evidence archive after the attempt.

## Current state after this implementation PR

Authorization issuer implemented: true. Authorization issued: false. Runtime execution performed: false. Next gate: explicit operator confirmation after merge.
