# AuraGateway CUDA 12.9 P3-P6 Runtime Install Diagnostics V2

## Executive result

Repository implementation only. No Kaggle, GPU, pip installation, model load, worker start, or model request is performed by this tranche.

## Evidence basis

- PR #175 merge authority: `1849c4b3f9cd36400b30d29ea3b3e67712251815`
- V1 failed saved version: `339375227`
- accepted failure boundary: `OFFLINE_TARGET_RUNTIME_INSTALLATION`
- accepted V1 root-cause state: `UNRESOLVED_PIP_SUBPROCESS_FAILURE`
- V1 authorization lifecycle: closed and non-reusable

## Inspection finding

The governed wheelhouse topology places 176 wheels beneath `wheelhouse/wheels`. V1 invoked pip with `--find-links <wheelhouse-root>`. The earlier offline compatibility verifier used `--find-links <wheelhouse-root>/wheels`.

This is a deterministic implementation defect that can prevent pip from discovering the governed wheels. It is not presented as the confirmed V1 runtime root cause because V1 did not preserve pip output.

## V2 behavior

- exact `wheelhouse/wheels` discovery path;
- model copy occurs only after installation and target-runtime validation;
- one bounded install process with no retry;
- structured process outcome: `PASSED`, `NONZERO_EXIT`, `TIMEOUT`, or `LAUNCH_ERROR`;
- return code, timing, bounded sanitized output tails, disk usage, target size, and diagnostic signals;
- deterministic terminal reports for P3, P4, P5, and P6;
- separate scratch and evidence roots;
- scratch deletion and cleanup receipt before bundling;
- reviewed file allowlist and 2 MiB evidence-ZIP ceiling.

## Action budget

```text
Kaggle sessions: 1
runtime installation attempts: 1
model loads: 3
worker starts: 3
model requests: 5
maximum output tokens per request: 32
benchmark trajectories: 0
external network requests: 0
hidden retries: 0
external spend: 0
```

## Regression coverage

The focused suite covers deterministic generation, exact authority binding, the corrected find-links path, install-before-model-copy ordering, nonzero exit capture, timeout capture, launch failure capture, bounded failure signals, P3-P6 terminal reports, evidence allowlisting, scratch exclusion, candidate boundaries, and no runtime authorization.

## Non-claims

V2 has not run. Successful installation, P3 startup, P4 inference, P5 cache behavior, P6 isolation, model quality, benchmark quality, deployment, and production readiness remain unproven.

## Next gate

Merge V2, then design and merge a separate single-use P3-P6 Execution Authorization V2 bound to the new notebook identity.
