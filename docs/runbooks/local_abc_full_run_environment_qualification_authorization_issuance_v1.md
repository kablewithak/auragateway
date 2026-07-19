# Local A/B/C Environment Qualification Authorization Issuance v1

## Purpose

Issue one short-lived authorization for the existing six-probe Kaggle environment
qualification package.

This runbook does not execute Kaggle, install packages, start workers, load a model,
perform model requests, generate runtime evidence, or authorize the 342-request benchmark.

## Governing authority

```text
PR #110 merge:
211a10757999b1b110cb1d9df172938cf6ed7969

Authorization-issuance review artifact Git blob:
61590be7fe1d10e8e9b38405cf634f4a0cae3e31

Authorization-issuance review SHA-256:
73e9a4f0642cce40ce6bc6ef875ee13ab81900f0bc7e768e0c4a9a6b6f0ec859
```

The issuance implementation must preserve:

```text
maximum authorization window: 240 minutes
maximum Kaggle sessions: 1
maximum workers: 2
maximum model requests: 8
maximum output tokens per request: 32
benchmark trajectory requests permitted: 0
network access permitted: false
credentials permitted: false
customer data permitted: false
external spend: R0 / $0
measured execution authorized: false
```

## Implementation boundary

The repository implementation PR adds the issuance runner, typed contract changes,
tests, and this runbook.

It must not contain a pre-generated final authorization. The final artifact is generated
only after the implementation PR is merged, the operator is on synchronized clean
`main`, and explicit operator confirmation is supplied. This prevents a stale
authorization window from being embedded in an implementation ZIP or pull request.

## Pre-issuance checks

Run from the repository root:

```powershell
git switch main
git pull --ff-only origin main
git status
git --no-pager log -1 --oneline
```

Required state:

```text
branch: main
working tree: clean
PR #110 is an ancestor of HEAD
final authorization artifact: absent
runtime evidence: absent
```

## Issue one authorization

The operator confirmation flag is mandatory.

```powershell
python -m auragateway.local_abc.full_abc_local_environment_qualification_execution_authorization_issuance `
    issue `
    --repo-root . `
    --operator-confirm `
    --window-minutes 240
```

The runner:

1. requires clean `main`;
2. verifies PR #110 ancestry;
3. verifies the exact review Git blob;
4. revalidates repository-native issuance inputs;
5. binds the execution request, materialization record, runtime manifest, and adapter;
6. writes one canonical authorization without overwriting an existing artifact;
7. records the confirmation time as `issued_at`;
8. limits `expires_at` to no more than 240 minutes later.

## Verify before any Kaggle activity

```powershell
python -m auragateway.local_abc.full_abc_local_environment_qualification_execution_authorization_issuance `
    verify `
    --repo-root .
```

Verification must report:

```text
authorization_valid=true
maximum_workers=2
maximum_kaggle_sessions=1
maximum_model_requests=8
maximum_output_tokens_per_request=32
benchmark_trajectory_requests_permitted=0
network_access_permitted=false
credentials_permitted=false
customer_data_permitted=false
external_spend=0
kaggle_session_started=false
runtime_evidence_generated=false
measured_execution_authorized=false
```

## Fail-closed behavior

Issuance stops if:

- the current branch is not `main`;
- the working tree is not clean;
- PR #110 is not an ancestor;
- the review blob or review content drifts;
- the final authorization already exists;
- runtime evidence already exists;
- any immutable input fails validation;
- the requested window exceeds 240 minutes;
- operator confirmation is absent.

The runner never overwrites an existing authorization.

## Expiry and recovery

An expired authorization is invalid.

Do not edit timestamps manually. Delete the expired local artifact only after confirming
that no Kaggle session used it, restore a clean `main`, and perform a separately governed
re-issuance. Never extend the window by modifying JSON.

## Non-claims

Authorization issuance does not prove:

- vLLM installation compatibility;
- model or tokenizer load;
- worker health;
- cache metric availability;
- reset correctness;
- environment qualification;
- cache reuse;
- latency improvement;
- quality non-inferiority;
- measured benchmark authorization;
- production readiness.
