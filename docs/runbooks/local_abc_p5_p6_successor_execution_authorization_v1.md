# Runbook: P5/P6 Successor Execution Authorization V1

## Static implementation phase

The implementation PR may only generate and validate:

- authorization architecture review;
- authorization implementation record.

It MUST NOT create:

- live execution authorization;
- consumption receipt;
- abandonment receipt;
- Kaggle runtime execution.

Static commands:

```text
python -m auragateway.local_abc.p5_p6_successor_execution_authorization_v1 generate --repo-root .
python -m auragateway.local_abc.p5_p6_successor_execution_authorization_v1 validate-implementation --repo-root .
```

## Post-merge issuance preconditions

Before issuance:

1. synchronize local `main` with `origin/main`;
2. confirm a clean repository;
3. verify the merged issuer;
4. observe Kaggle notebook settings freshly;
5. confirm:
   - accelerator = GPU T4 x2;
   - allocated GPU count = 2;
   - Internet = OFF;
   - wheelhouse attachment count = 1;
   - model snapshot attachment count = 1;
   - worker 1 mapping = GPU 0;
   - worker 2 mapping = GPU 1;
6. create canonical `IssuanceConfirmation` JSON outside the governed static
   candidate;
7. issue once.

Platform observation and operator confirmation must be no more than 15 minutes
old at issuance.

## Live lifecycle

Issue:

```text
python -m auragateway.local_abc.p5_p6_successor_execution_authorization_v1 issue --repo-root . --confirmation-json <path>
```

Verify immediately before execution:

```text
python -m auragateway.local_abc.p5_p6_successor_execution_authorization_v1 verify --repo-root .
```

Consume after any terminal execution attempt:

```text
python -m auragateway.local_abc.p5_p6_successor_execution_authorization_v1 consume --repo-root . --outcome <OUTCOME> [--saved-version-id <ID>] [--evidence-zip-sha256 <SHA>] [--terminal-log-sha256 <SHA>]
```

If authority is issued but execution will not occur:

```text
python -m auragateway.local_abc.p5_p6_successor_execution_authorization_v1 abandon --repo-root . --reason <REASON>
```

## Hard stop conditions

Do not execute if:

- authorization is absent;
- authorization is expired;
- terminal receipt already exists;
- repository or implementation identity drifted;
- platform observation is stale;
- T4 x2 is unavailable;
- Internet is enabled;
- required inputs are not exactly attached;
- the live authorization fails verification.

## Publication boundary

Transient authorization, consumption, and abandonment files remain untracked.
They are evidence inputs for a later acceptance transaction, not static issuer
implementation artifacts.
