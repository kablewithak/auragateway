# P3-P6 Runtime Diagnostic Failure Acceptance V2

## Accepted result

Saved version `339387641` is a governed FAILED run. Installation passed, one model load and one worker start were attempted, and P3 failed before readiness. P4, P5, and P6 were deterministically `NOT_RUN`.

## Confirmed first divergence

The parent API-server process imported vLLM 0.19.1 from the target runtime. vLLM then launched a fresh `/usr/bin/python3` registry subprocess. That child could not import `vllm`, causing Qwen2 model-architecture inspection and `ModelConfig` construction to fail.

## Classification

- failure code: `P3_P6_WORKER_STARTUP_FAILED`
- failed probe: `P3`
- installation: `PASSED`
- first divergence: `TARGET_RUNTIME_IMPORT_PATH_NOT_PROPAGATED_TO_VLLM_REGISTRY_SUBPROCESS`
- violated invariant: `TARGET_RUNTIME_PROCESS_TREE_IMPORT_CLOSURE`
- root-cause evidence: sufficient
- remediation effectiveness: not established

## Non-claims

This acceptance does not prove P3 readiness, Qwen compatibility after remediation, `TRITON_ATTN` realization, P4 inference, P5 cache behavior, P6 isolation, deployment readiness, or production readiness.
