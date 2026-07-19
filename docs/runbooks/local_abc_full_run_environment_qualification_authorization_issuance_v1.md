# Local A/B/C Environment Qualification Authorization Issuance v1

## Purpose

Issue one short-lived authorization for the existing six-probe Kaggle environment
qualification package.

This runbook does not execute Kaggle, install packages, start workers, load a model,
perform model requests, generate runtime evidence, or authorize the 342-request benchmark.

## Governing authority

```text
Harness source authority:
PR #112 merge:
be1bfadd8a8aa3f0a2f6143d6a73f082f1090c50

Authorization source authority and historical review authority:
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

## Source-authority semantics

`source_main_merge_commit` in the final authorization identifies the merged main
commit that approved the authorization contract consumed by the frozen runtime
loader. It is therefore bound to PR #110 (`211a107...`).

The harness build lineage is independent and remains bound to PR #112
(`be1bfad...`) through the harness rematerialization record and launcher input
contract. The harness source commit must never be substituted into the
authorization source-authority field.

Before any authorization file is written, the issuance runner serializes the
candidate and validates it through the exact preserved frozen-loader
compatibility model. A mismatch fails with
`CURRENT_ISSUANCE_FROZEN_LOADER_PARITY_FAILED`.

## Harness rematerialization prerequisite

The stale `4dfd799` harness dataset is not eligible for another qualification run.

Authorization issuance now requires the canonical repository record:

```text
benchmarks/local_abc/
auragateway_full_abc_local_environment_qualification_
harness_rematerialization_v1.json
```

That record binds:

```text
replacement producer:
kabomolefe/ag-harness-materializer-input-v3

producer version:
1

replacement directory SHA-256:
4a371c80aef605c4f1ab5617c21ce43bd0939ad449ffcbcadab656878d785a2e

parity evidence SHA-256:
b986f3b82785f86dea2c8fb368dd8ae4def7ee3d7b00f44637f77f3d28b1971b

parity status:
HARNESS_AUTHORIZATION_PARITY_PASSED
```

The model snapshot and vLLM wheel remain unchanged.

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
PR #112 is an ancestor of HEAD
historical PR #110 review blob remains intact
harness rematerialization record validates
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
2. verifies PR #112 ancestry;
3. verifies the exact historical PR #110 review Git blob;
4. validates the parity-approved harness rematerialization record;
5. revalidates repository-native issuance inputs;
6. binds the execution request, refreshed materialization record, runtime manifest, and adapter;
7. writes one canonical authorization without overwriting an existing artifact;
8. records the confirmation time as `issued_at`;
9. limits `expires_at` to no more than 240 minutes later.

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
- PR #112 is not an ancestor;
- the historical review blob or review content drifts;
- the harness rematerialization record or parity-approved identities drift;
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
