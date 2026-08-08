# ADR: Variance-pilot runtime lineage reconciliation V1

Date: 2026-08-08

## Status

Proposed for merge.

## Context

Variance Pilot V1 control-plane implementation is merged on main `b1efe4d65aea2572dac0d0c9c440245dd00a0b43` and remains
non-authorizing.

Before building its Kaggle runtime launcher, current repository evidence exposes two different
runtime lineages.

The preflight-v3 final benchmark plan names:

- vLLM `0.25.1+cu129`
- vLLM wheel SHA-256
  `9e206f370c934a2d4b6b1f05d3d09708d344e05d80260189ef19f60755709431`
- torch `2.11.0+cu129`
- CUDA `12.9`

That same planning line says current full-run environment requalification is required and that
the Kaggle runtime lock has not yet been generated.

The governed P5/P6 successor execution that was actually accepted used a different offline
runtime line:

- vLLM `0.19.1`
- torch `2.10.0+cu129`
- Triton `3.6.0`
- TRITON_ATTN
- the same Qwen model and revision

## Problem

The variance pilot measures operational properties including TTFT, prefill duration, worker
asymmetry, cache consistency, and interruption behavior.

Those measurements are not safely portable across different vLLM/torch runtime lines.

Running the pilot on the accepted 0.19.1 runtime while keeping the final benchmark planned on
0.25.1 would make the repetition-count decision non-transferable.

## Decision

Block variance-pilot runtime-launcher construction until the exact preflight-v3 runtime line is
materialized and governed P5/P6 qualification is re-established on that exact runtime.

Do not rewrite the final A/B/C plan to match the earlier P5/P6 runtime merely because that
runtime already passed qualification.

## Alternatives

### A. Rebase final planning to vLLM 0.19.1 / torch 2.10

Rejected for now.

This would cascade through condition fingerprints, planned-run-ledger identity, pilot assets,
authorization bindings, and readiness lineage.

### B. Preserve preflight-v3 and qualify its exact runtime

Selected.

This preserves the already-frozen causal planning boundary and makes runtime qualification a
real predecessor of the pilot rather than silently changing the experiment.

## Required sequence

1. Prove or materialize the exact planned vLLM wheel.
2. Freeze the offline Kaggle runtime dependency lock.
3. Build repository-only exact-runtime qualification assets.
4. Merge them without execution.
5. Issue a separate single-use qualification authorization.
6. Execute bounded P5/P6 qualification on the exact planned runtime.
7. Accept or classify that evidence.
8. Only after acceptance build variance-pilot launcher readiness.

## Authorization state

```text
pilot_execution_authorized=false
runtime_execution_authorized=false
final_measured_abc_execution_authorized=false
```

## Non-claims

This ADR does not revoke the historical P5/P6 pass. It states only that the accepted pass does
not establish operational variance for a different planned runtime.
