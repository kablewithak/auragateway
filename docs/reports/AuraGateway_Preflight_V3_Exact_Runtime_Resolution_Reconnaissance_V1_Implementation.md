# AuraGateway Preflight-v3 Exact Runtime Resolution Reconnaissance V1 — Implementation

## Status

`IMPLEMENTED_NOT_EXECUTED`

Implementation base main:

`15d8c4db122eb50c2f639748bc06f98bae70b167`

## Boundary

This tranche implements the CPU-only dependency-resolution reconnaissance
selected by the merged exact-runtime materialization design.

It does not resolve dependencies locally, materialize wheels, use a GPU, load
a model, issue a model request, freeze the exact runtime lock, or authorize
the variance pilot.

## Runtime target

```text
Python=3.12
CUDA=12.9
vLLM=0.25.1+cu129
vLLM planned SHA-256=9e206f370c934a2d4b6b1f05d3d09708d344e05d80260189ef19f60755709431
torch=2.11.0+cu129
```

## Notebook behavior

The notebook:

1. requires Python 3.12;
2. rejects attached Kaggle inputs;
3. rejects known credential environment variables without printing values;
4. discovers the single v0.25.1 CUDA-12.9 vLLM release wheel from the GitHub
   release API;
5. runs pip with `--dry-run`, `--ignore-installed`, `--only-binary=:all:`,
   and `--report`;
6. requests the exact torch 2.11.0+cu129 runtime;
7. records every resolved wheel URL, hostname, distribution, version, and
   SHA-256;
8. verifies the resolved vLLM SHA equals the preflight-v3 SHA;
9. snapshots installed distributions before and after to detect mutation;
10. uses a temporary pip cache and retains zero wheel files;
11. emits five metadata-only evidence files plus a transport ZIP.

## Required evidence

- `resolved_artifacts.json`
- `resolver_report.json`
- `host_policy.json`
- `resolution_receipt.json`
- `output_manifest.json`

Host acceptance is deliberately not automatic. Exact hosts are enumerated and
marked pending repository review before a new lock can be frozen.

## Failure handling

The notebook fails closed on:

- Python-version drift;
- attached Kaggle inputs;
- credential presence;
- ambiguous vLLM release asset identity;
- pip resolution failure;
- non-HTTPS or credential-bearing artifact URLs;
- query/fragment-bearing unstable artifact URLs;
- non-wheel artifacts;
- missing artifact SHA-256;
- duplicate distributions;
- vLLM version/SHA mismatch;
- torch version mismatch;
- package-environment mutation;
- retained wheel artifacts.

A failure writes `resolution_failure.json` with bounded metadata and hashes of
resolver stdout/stderr. It does not claim qualification.

## Current authorization state

```text
exact_runtime_resolution_lock_frozen=false
exact_runtime_materialized=false
exact_runtime_offline_verified=false
runtime_execution_authorized=false
pilot_execution_authorized=false
final_measured_abc_execution_authorized=false
```

## Non-claims

This implementation is production-shaped repository logic. It is not executed
target-environment evidence and is not production-ready.

## Next gate

`merge_then_execute_preflight_v3_exact_runtime_resolution_reconnaissance_v1`
