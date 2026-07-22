# Local A/B/C Environment Qualification Authorization Issuance v1

## CURRENT STATUS: ISSUER IMPLEMENTED; AUTHORIZATION ABSENT

The repository now contains a fresh CUDA 12.9 authorization issuer for the current
operational-input boundary. The implementation must merge without creating the
short-lived authorization artifact.

Current repository authority:

```text
PR #135 integration merge:
3ea2cf60db7057f94cdbda9060587e5e6881ef28

Current harness source:
426f57dd11dddc2fb8e5a703721c2189abc7a0ff

Current harness directory SHA-256:
c3ea4ae6d047a8b3f3d5afc517e26c4f13fb4a82e48e3cf28cdfabdc343230e6

Current runtime manifest SHA-256:
f7289cee9414d03d88ceb4775198e15ff9446fd99771a58c187de0d4264ef94a

Current materialization record SHA-256:
284b488dece09e6b17dcf72e4dea69bbdadd440356ce353622b100c38a02100a

Current runtime adapter SHA-256:
aec461dcd595bfa3af286d88832ec7ef1ca2b416adca6a548f102d9543fb8dba

Current launcher source SHA-256:
7c0f7f1d466fd68a56d6b77c6e16cf69343491710052818743327b51f1d57f16

Current launcher notebook SHA-256:
7ec60fd0a162f50961f8ff66a6e3dec3c68a15617109fdc7530b2ec380294de9

Fresh readiness review SHA-256:
2a0463c48e1a8ffdd4c93f7ed20cc4c60bd7925602a09a59a7b9d9dc3545f00b
```

## Purpose

Create one non-overwriting, time-bounded authorization only after:

1. the issuer implementation has merged;
2. local `main` equals `origin/main`;
3. the working tree is clean;
4. the operator gives explicit operator confirmation immediately before use.

The implementation does not:

- issue authorization during the implementation PR;
- start Kaggle;
- install the CUDA 12.9 wheelhouse;
- load a model or tokenizer;
- start workers;
- perform model requests;
- create runtime evidence;
- authorize benchmark trajectories;
- authorize measured A/B/C execution.

## Frozen runtime compatibility

The rematerialized harness accepts the preserved version `1.0.0` authorization shape.
Its payload must retain:

```text
source_main_merge_commit:
211a10757999b1b110cb1d9df172938cf6ed7969

review_git_blob_sha:
61590be7fe1d10e8e9b38405cf634f4a0cae3e31
```

Those fields are compatibility authorities, not the current harness identity. The
issuer separately verifies the PR #135 integration merge, current harness source,
fresh readiness review, current manifest, current materialization record, current
runtime adapter, and current launcher before constructing the frozen-compatible
payload.

The launcher preserves dynamic authorization provenance through:

```text
CONTROL_PACKAGE_AUTHORIZATION_PARITY
```

The control materializer must copy the authorization source field from the actual
issued payload. It must not replace that field with the current harness commit.

## Hard limits

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
external spend: 0
measured execution authorized: false
```

## Validate the implementation boundary

Run from the repository root while the final authorization remains absent:

```powershell
python -m auragateway.local_abc.full_abc_local_environment_qualification_execution_authorization_issuance `
    validate-implementation `
    --repo-root .
```

Required output includes:

```text
status=FRESH_CU129_AUTHORIZATION_ISSUER_READY
authorization_issued=false
kaggle_session_started=false
worker_started=false
model_requests_performed=0
benchmark_trajectory_requests_permitted=0
next_gate=explicit_operator_confirmation_then_issue_fresh_authorization
```

Also validate the complete authority graph:

```powershell
python -m auragateway.local_abc.full_abc_local_environment_qualification_cu129_authority_graph `
    --repo-root .
```

Required output includes:

```text
status=CURRENT_CU129_AUTHORIZATION_ISSUER_IMPLEMENTED_AUTHORIZATION_ABSENT
fresh_cu129_authorization_review_required=false
fresh_cu129_authorization_issuer_implemented=true
authorization_issued=false
runtime_execution_performed=false
model_requests_performed=0
```

## Implementation-PR prohibition

Do not run the `issue` command while the issuer implementation is unmerged or while
working on its feature branch. The implementation PR must not contain:

```text
benchmarks/local_abc/
auragateway_full_abc_local_full_run_environment_qualification_
execution_authorization_v1.json
```

The issuer rejects tracked authorization artifacts and never overwrites an existing
artifact.

## Post-merge issuance gate

After the issuer merges, synchronize `main` and obtain explicit operator confirmation.
Issue the authorization only immediately before control materialization:

```powershell
python -m auragateway.local_abc.full_abc_local_environment_qualification_execution_authorization_issuance `
    issue `
    --repo-root . `
    --operator-confirm `
    --window-minutes 240
```

The command must run from clean synchronized `main`. The generated authorization is an
untracked transient artifact. Do not stage or commit it.

Verify the live window before control materialization:

```powershell
python -m auragateway.local_abc.full_abc_local_environment_qualification_execution_authorization_issuance `
    verify `
    --repo-root .
```

The verification command permits exactly one working-tree difference: the untracked
final authorization path. Any additional change fails closed.

## Next gate after issuance

```text
full_abc_local_full_run_environment_qualification_control_materialization
```

The next operation is CPU-only control-package materialization. It is not the GPU
qualification run itself.

## Expiry and cleanup

An expired authorization must not be refreshed in place or overwritten. Preserve its
identity in the downstream control/evidence lineage, then delete the transient local
file before issuing a replacement under a separately authorized retry.

```powershell
$AuthorizationPath = Join-Path (Get-Location) `
    "benchmarks/local_abc/auragateway_full_abc_local_full_run_environment_qualification_execution_authorization_v1.json"

if (Test-Path -LiteralPath $AuthorizationPath) {
    Remove-Item -LiteralPath $AuthorizationPath -Force
}
```

## Fail-closed conditions

Issuance stops when:

- local `main` differs from `origin/main`;
- the tree is dirty before issuance;
- PR #135 is not an ancestor;
- the current harness source is not an ancestor;
- the frozen authorization-source parity package fails;
- current harness evidence integration fails;
- operational input closure is not `PASSED`;
- the readiness review, request, manifest, materialization, adapter, or launcher drifts;
- the materialization record does not project to the portable runtime manifest;
- the launcher-control authorization-source policy drifts;
- runtime evidence already exists;
- the final authorization is tracked or already exists;
- the requested window exceeds 240 minutes;
- the payload fails the frozen runtime-loader schema;
- atomic non-overwriting creation is unavailable.

## Non-claims

This issuer implementation does not prove:

- wheelhouse installation on a fresh Kaggle image;
- model or tokenizer load;
- worker health;
- cache telemetry availability;
- cache reset correctness;
- environment qualification;
- same-worker cache reuse;
- cross-worker cache isolation;
- latency or cost improvement;
- quality non-inferiority;
- measured A/B/C authorization;
- customer-data readiness;
- production readiness.
