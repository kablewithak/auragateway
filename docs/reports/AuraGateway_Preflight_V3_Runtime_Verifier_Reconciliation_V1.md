# AuraGateway Preflight-v3 Runtime Verifier Reconciliation V1

## Authority

```text
sequencing_authority=HANDOVER_V17_AND_CURRENT_REPOSITORY_EVIDENCE
current_boundary=P0_FINAL_RUNTIME_VERIFIER_RECONCILIATION
original_prd_role=HISTORICAL_NORTH_STAR_AND_DESIGN_CONTEXT_ONLY
```

The July Controlled Local A/B/C Completion Extension PRD is not used as the
current stage map. PR #211 and V17 supersede that sequencing for the exact final
runtime lineage.

## Decision

```text
V2 saved version=341096416
V2 technical status=FAILED_PENDING_REVIEW
V2 repository disposition=ACCEPTED_DIAGNOSTIC_FAILURE
classification=STALE_VERSION_BOUND_NATIVE_EXTENSION_PROBE
runtime incompatibility established=false
```

## Exact V2 evidence

```text
executed notebook SHA-256=
81dade4abf79f1a5984101f9e7d0091f2fb748437b1aece0538678db633202cc

execution log SHA-256=
7b4ae0b97c6caae4f6ea2f099a691ca28a9fdf7215be6f2491c74dff0c2301aa

evidence ZIP SHA-256=
10ed35bb8e9f9718eb7cd7e945ed8cf8503414c8ef400e70109b46fceff4e96b
```

V2 passed every required role except `vllm_native_extension`.

The passing vLLM module probe returned code `0` and observed semantic version
`0.25.1`. The failed native probe returned code `1` while importing
`vllm._C`.

## First divergence

```text
role=vllm_native_extension
probe=vllm._C
status=FAILED
returncode=1
exception=ModuleNotFoundError
```

Exact vLLM `v0.25.1` CUDA source/build evidence identifies
`vllm._C_stable_libtorch` as the CUDA-platform native module. Therefore the V2
probe is stale for the target execution path.

## Startup finding

V2 inherited ambient process state and repeatedly emitted:

```text
Error in sitecustomize
ModuleNotFoundError: No module named 'wrapt'
```

The warning also appears on successful probes. The supported conclusion is:

```text
full_python_startup_isolation_proven=false
wrapt_causal_role=UNPROVEN
```

No dependency mutation is justified by this warning.

## Historical controls recovered

The project already contains accepted design evidence for:

```text
PYTHONPATH=<removed>
PYTHONHOME=<removed>
PYTHONNOUSERSITE=1
python_startup_policy=NO_SITE_WITH_CONTROLLED_SITE_BOOTSTRAP
sitecustomize_policy=CONTROLLED_SENTINEL_BEFORE_SITE_MAIN
usercustomize_policy=CONTROLLED_SENTINEL_BEFORE_SITE_MAIN
external_package_path_policy=REMOVE_NON_TARGET_SITE_AND_DIST_PACKAGES
canonical_loader_policy=TARGET_NVIDIA_LIBRARIES_PREPENDED
real_driver_directory=/usr/local/nvidia/lib64
cuda_stub_policy=REJECT
```

These controls guide the final verifier but are not promoted into current-line
qualification.

## Frozen current-line capability contract

```text
P0_FINAL_RUNTIME_VERIFIER_RECONCILIATION
        ↓
L0 artifact closure
L1 offline installation closure
L2 controlled Python startup closure
L3 native-extension inventory
L4 native-loader closure and provenance
L5 vLLM 0.25.1 CUDA-platform capability
        ↓
only after accepted compatibility:
exact-runtime P5/P6 requalification
```

Required CUDA native module:

```text
vllm._C_stable_libtorch
```

A future PASS must prove acceptable native origins as well as successful import.

## Safety state

```text
model_loads_permitted=0
worker_startups_permitted=0
model_requests_permitted=0
benchmark_trajectories_permitted=0
exact_runtime_offline_verified=false
p5_p6_exact_runtime_requalified=false
runtime_execution_authorized=false
pilot_execution_authorized=false
final_measured_abc_execution_authorized=false
next_expensive_execution_permitted=false
```

## Sequencing consequence

This reconciliation closes the V17 static verifier-reconciliation question. It
does not resurrect the original PRD gate numbering as current authority.

The next repository engineering gate is implementation of the **final offline
verifier** from this reconciled capability contract. Execution of that verifier
remains a later, separately governed transition.

## Next gate

```text
design_and_implement_final_preflight_v3_exact_runtime_offline_verifier_from_reconciled_capability_contract
```
