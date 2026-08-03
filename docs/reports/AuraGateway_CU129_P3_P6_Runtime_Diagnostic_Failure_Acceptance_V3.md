# AuraGateway P3-P6 Runtime Diagnostic Failure Acceptance V3

## Decision

Saved version `339943910` remains a governed `FAILED` attempt.

The reported failure code is retained as historical runtime output:

```text
P3_P6_EXPLICIT_BACKEND_NOT_REALIZED
```

Its semantic disposition is:

```text
QUARANTINED_INVALID_DIAGNOSTIC
```

## Established observations

- offline target-runtime installation passed;
- the nested Python process-tree import-closure gate passed;
- the first worker loaded the exact model snapshot;
- `/health` returned HTTP 200;
- `/v1/models` returned HTTP 200 and the exact inventory check returned;
- vLLM 0.19.1 emitted the explicit TRITON_ATTN startup-selection record;
- worker stdout and stderr were retained without truncation;
- no model request, benchmark trajectory, network request, hidden retry, or
  external spend occurred;
- scratch cleanup passed.

## Confirmed first divergence

```text
BACKEND_MARKER_PREDICATE_INCOMPATIBLE_WITH_PINNED_VLLM_0_19_1_RUNTIME_MARKER
```

The classifier required:

```python
return "triton_attn" in text and "attention backend" in text
```

The authoritative runtime line was:

```text
Using AttentionBackendEnum.TRITON_ATTN backend.
```

The first predicate component matched. The second did not.

## Evidence limitations

The saved-version notebook bytes and rendered HTML were not preserved.
Therefore, executed notebook source identity is not independently verified.
Formal P3 acceptance, request-level attention execution, P4, P5, P6, complete
native-library provenance, and structured GPU teardown are not established.

## Next gate

```text
design_and_merge_p3_p6_runtime_evidence_contract_hardening_v4
```
