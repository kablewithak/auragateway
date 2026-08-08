# AuraGateway Preflight-v3 Exact Runtime Wheelhouse Materializer V1 — Implementation

## Status

`IMPLEMENTED_NOT_EXECUTED`

Base main:

`250cf837408858d5d6354c5ed7ac5f9f1db9cd73`

## Frozen authority

```text
exact_resolution_lock_sha256=1294394ac476336b103b036d8654a49e4ae78c25c912ca5729cd94f982384f3c
package_count=196
artifact_authority_host_count=5
```

The materializer embeds the exact frozen lock bytes and refuses to run if the embedded SHA differs
from the repository-accepted lock.

## Behavior

The notebook downloads exactly 196 locked wheel URLs and verifies every wheel against the frozen
SHA-256 before promoting its temporary file into the wheelhouse.

It does not invoke pip dependency resolution, pip download, package installation, GPU APIs, vLLM,
model loading, or benchmark execution.

## Transport redirect reconciliation

The five-host lock remains the artifact-authority boundary.

The vLLM release artifact is governed by a stable `github.com` release URL, but GitHub serves the
bytes through an HTTPS redirect to `release-assets.githubusercontent.com`. The materializer therefore
treats this as a transport redirect rather than a sixth artifact authority.

Only this cross-host redirect is permitted:

```text
github.com -> release-assets.githubusercontent.com
```

At most one redirect is permitted per artifact. Other cross-host redirects fail closed. The signed
redirect URL is never persisted; only source host, destination host, and status code are retained.

All downloaded bytes remain governed by the exact frozen artifact SHA-256.

## Materialized output

```text
auragateway_preflight_v3_exact_runtime_wheelhouse_v1/
├── wheels/                         # exactly 196 wheels
├── resolution_lock.json            # exact frozen lock bytes
├── requirements.lock.txt           # exact name/version/hash install contract
├── materialization.lock.txt        # exact wheel path/hash contract
├── runtime_manifest.json
├── sha256_manifest.json            # 196 wheels + 4 control files
└── materialization_receipt.json
```

A small `materialization_evidence.zip` contains only control evidence and no wheel payloads.

## Evidence boundary

Successful materialization means:

```text
materialization_status=PASSED_PENDING_REPOSITORY_ACCEPTANCE
wheelhouse_materialized=true
exact_runtime_materialized=false
exact_runtime_offline_verified=false
qualification_claimed=false
```

The repository must accept the saved Kaggle materialization before `exact_runtime_materialized` can
be promoted to true.

## Current authorization

```text
runtime_execution_authorized=false
pilot_execution_authorized=false
final_measured_abc_execution_authorized=false
```

## Next gate

`merge_then_execute_preflight_v3_exact_runtime_wheelhouse_materializer_v1`
