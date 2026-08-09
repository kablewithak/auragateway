# AuraGateway Preflight V4 Semantic Channel Reconciliation Certificate V1

## Determination

`DIAGNOSTIC_HARNESS_DEFECT`

Failure code:

`EVIDENCE_REPRESENTATION_REUSED_AS_SEMANTIC_INPUT`

Saved version:

`341211001`

Evidence ZIP SHA-256:

`94e73e06c2627c9c03fac85894654800e31fbd6f55b0c6157ea0d09097ef92c8`

Runtime incompatibility is not established.

## Machine-audited V4 topology

V4 performs evidence transformation in `run_probe()` before later semantic
validation:

`raw subprocess output -> sanitize/truncate -> stdout_excerpt -> semantic parse`

The static reconciliation binds:

- 19 semantic `stdout_excerpt` read sites;
- 18 distinct semantic roles reading `stdout_excerpt`;
- zero semantic `stderr_excerpt` read sites;
- five deterministic path-bearing false-negative roles.

The deterministic role set is:

- `controlled_python_startup`
- `target_native_inventory`
- `native_linker_static_provenance`
- `vllm_native_extension`
- `native_runtime_provenance`

## Historical mechanism recovery

The July controlled-startup evidence proves that semantic booleans were computed
inside the child process before evidence path sanitization.

The P4 V2 native runtime hardening supplies a selective native-origin dataflow pattern:

`raw Path -> resolve/classify for semantic truth` and, independently, `raw Path -> sanitize for persisted origin evidence`

## Required successor gates

```text
semantic_decisions_reading_stdout_excerpt=0
semantic_decisions_reading_stderr_excerpt=0
lossy_transformations_before_semantic_decision=0
truncation_before_semantic_decision=0
path_decisions_use_raw_canonical_paths=true
evidence_policy_is_terminal=true
sanitizer_metamorphic_invariance=PASS
excerpt_length_metamorphic_invariance=PASS
symlink_escape_negative_case=PASS
ambient_python_native_negative_case=PASS
cuda_stub_negative_case=PASS
real_driver_positive_case=PASS
unknown_native_origin_fails_closed=PASS
statically_predictable_successor_failures=0
```

## Non-claims

```text
runtime_incompatibility_established=false
exact_runtime_offline_verified=false
p5_p6_exact_runtime_requalified=false
runtime_execution_authorized=false
pilot_execution_authorized=false
final_measured_abc_execution_authorized=false
next_kaggle_execution_authorized=false
```

## Next gate

`design_semantic_channel_safe_final_offline_verifier_v5_successor`
