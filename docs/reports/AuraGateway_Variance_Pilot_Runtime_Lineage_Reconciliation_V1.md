# AuraGateway Variance-Pilot Runtime Lineage Reconciliation V1

## Decision

`BLOCK_RUNTIME_LAUNCHER_UNTIL_EXACT_RUNTIME_LINEAGE_REQUALIFIED`

Source main: `b1efe4d65aea2572dac0d0c9c440245dd00a0b43`

## Divergence

### Preflight-v3 final-run plan

```text
vllm=0.25.1+cu129
torch=2.11.0+cu129
cuda=12.9
vllm_wheel_sha256=9e206f370c934a2d4b6b1f05d3d09708d344e05d80260189ef19f60755709431
current_full_run_environment_requalification_required=true
kaggle_runtime_lock_generated=false
```

### Governed accepted P5/P6 runtime

```text
vllm=0.19.1
torch=2.10.0+cu129
triton=3.6.0
attention_backend=TRITON_ATTN
current_line_p5_pass_accepted=true
current_line_p6_pass_accepted=true
```

## Why this matters

The variance pilot is supposed to validate operational stability for the runtime that will
produce the final measurements. TTFT, prefill duration, cache telemetry, worker asymmetry, and
interruption behavior can all change when the runtime changes.

## Selected resolution

Preserve the preflight-v3 final-run plan and qualify its exact runtime before constructing the
pilot launcher.

## Next gate

`materialize_and_qualify_preflight_v3_exact_runtime_line_v1`
