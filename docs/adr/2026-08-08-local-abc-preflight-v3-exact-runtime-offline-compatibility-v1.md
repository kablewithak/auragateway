# ADR: Preflight-v3 exact-runtime offline compatibility verifier V1

Date: 2026-08-08

## Status

Approved for implementation.

## Context

The accepted materialization line now binds:

```text
main=8d65113561374e7ce6a416790251a238c6240ed7
materialization_acceptance_sha256=042150fdc207e0f0a13f3c40209fc308b133b7abbbef5980130d23ec64c51725
materializer_script_version_id=341083505
resolution_lock_sha256=1294394ac476336b103b036d8654a49e4ae78c25c912ca5729cd94f982384f3c
package_count=196
sha_manifest_entry_count=200
total_wheel_bytes=6164913809
```

The wheelhouse is materialized, but installation/runtime compatibility remains unproven.

## Decision

Implement one fresh Internet-Off T4 x2 diagnostic verifier.

The verifier reuses the proven historical mechanism of creating a target with
`venv --without-pip` and using base pip's global `--python` interface as the
installation executor. It does not reuse the historical 176-wheel runtime or
its PASS/FAIL authority.

The new verifier first stream-validates the accepted 196-wheel input, then
performs an isolated `--no-index --require-hashes --no-deps` installation and
explicit runtime probes.

## Required runtime identities

```text
Python=3.12
CUDA variant=cu129
torch=2.11.0+cu129
torchaudio=2.11.0+cu129
torchvision=0.26.0+cu129
torch.version.cuda=12.9
transformers=5.14.1
triton=3.6.0
vLLM=0.25.1+cu129
GPU topology=T4 x2
```

## Failure semantics

A failed role is evidence. Downstream roles are marked
`BLOCKED_BY_UPSTREAM_FAILURE`; they are not mislabeled as independently failed.

The saved Version 1 must be preserved whether the technical result passes or
fails.

## Non-claims

Implementation does not prove offline compatibility. Execution does not
authorize model loading, worker startup, P5/P6 qualification, variance-pilot
execution, final measured A/B/C, or production readiness.
