# AuraGateway CUDA 12.9 vLLM CLI Contract Hardening Report

## Outcome

The failure is classified as a deterministic harness-to-runtime CLI contract
defect, not a GPU, model-identity, authorization, or cache result.

## Evidence

- control materialization completed with four files and no runtime execution;
- qualification failed during initial worker startup;
- worker 1 returned code 2 before health readiness;
- the bounded diagnostic captured the unsupported
  `--disable-log-requests` option;
- zero model requests and zero benchmark trajectories were performed.

## Implemented boundary

The canonical command now uses `--no-enable-log-requests`. The controlled
dependency-lock process validates every governed long option against the
installed pinned `api_server --help` output before either worker is spawned.

The active materialized harness remains unchanged. Fresh issuance is blocked
until the corrected source is rematerialized and integrated.

## Non-claims

No environment qualification, model-load success, cache qualification,
measured improvement, quality non-inferiority, or production readiness is
claimed.
