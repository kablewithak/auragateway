# AuraGateway Preflight-v3 Exact Runtime Materialization V1 — Design

## Decision

`EXTEND_EXISTING_CU129_MATERIALIZER_WITH_NEW_EXACT_RUNTIME_LOCK`

Source main: `5e5f64a47db9665e7044748d93a554aa9f55b606`

## Classification

```text
direct reuse = NO
extension    = YES
from scratch = NO
```

Existing machinery is reusable as a pattern, but its 0.19.1 / torch 2.10
resolution lock is not valid authority for the planned 0.25.1+cu129 /
torch 2.11.0+cu129 runtime.

## Next slice

Build a new CPU-only exact-runtime resolution reconnaissance. It must resolve
and record the complete dependency closure without package installation or
model execution.

## Current state

```text
runtime_execution_authorized=false
pilot_execution_authorized=false
final_measured_abc_execution_authorized=false
```

## Next gate

`implement_preflight_v3_exact_runtime_resolution_reconnaissance_v1`
