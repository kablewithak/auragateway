# AuraGateway Preflight V5 Semantic Boundary Design Certificate V1

## Result

The V5 successor architecture is defined around a typed one-way semantic
boundary:

`RawProbeExecution -> TypedSemanticObservation -> ProbeDecision -> EvidenceProjection`

Required static results:

semantic_decisions_reading_stdout_excerpt=0
semantic_decisions_reading_stderr_excerpt=0
lossy_transformations_before_semantic_decision=0
truncation_before_semantic_decision=0
path_decisions_use_raw_canonical_paths=true
evidence_policy_is_terminal=true
statically_predictable_successor_failures=0

Required synthetic regressions:

sanitizer_metamorphic_invariance=PASS
excerpt_length_metamorphic_invariance=PASS
symlink_escape_negative_case=PASS
ambient_python_native_negative_case=PASS
cuda_stub_negative_case=PASS
real_driver_positive_case=PASS
unknown_native_origin_fails_closed=PASS

## Safety

This design tranche performs no Kaggle execution, package installation, model
loading, worker startup, model request, P5/P6 execution, pilot execution, or
measured A/B/C execution.

runtime_execution_authorized=false
pilot_execution_authorized=false
final_measured_abc_execution_authorized=false
next_kaggle_execution_authorized=false

## Non-claims

This is not exact-runtime qualification and is not a successful native/CUDA
runtime result.

## Next gate

implement_final_offline_verifier_v5_from_accepted_semantic_boundary
