# ADR: Preflight-v3 runtime verifier reconciliation V1

Date: 2026-08-09

## Status

Approved for repository reconciliation acceptance.

## Authority boundary

Current sequencing authority is:

```text
fresh repository evidence
+
Project Handover V17
+
Identity Registry V17
+
Workflow Guide V17
```

The original Controlled Local A/B/C Completion Extension PRD remains useful for
North-Star intent, experimental invariants, quality requirements, and final
non-claims. It is a July 2026 design baseline and is **not** used as the current
runtime-qualification stage map after the accepted PR #211 lineage decision and
the subsequent exact-runtime materialization / V1 / V2 work.

V17 introduces a newer prerequisite boundary before exact-runtime P5/P6:

```text
P0-FINAL-RUNTIME
  exact 196-wheel final-runtime identity
      ↓
  offline deterministic installation
      ↓
  controlled Python startup
      ↓
  native extension inventory
      ↓
  native loader closure/provenance
      ↓
  exact vLLM 0.25.1 CUDA platform capability
      ↓
  exact-runtime P5/P6 requalification
```

This ADR operates only inside that current prerequisite boundary.

## Context

The exact preflight-v3 final runtime is already resolved and materialized as a
196-wheel offline closure. Offline Verifier V1 established successful offline
installation, exact distribution inventory, T4 x2 visibility, Torch
`2.11.0+cu129` with CUDA `12.9`, Transformers `5.14.1`, Triton `3.6.0`, and a
successful `import vllm`. V1 was accepted as a verifier false negative because
it compared the vLLM distribution identity `0.25.1+cu129` with the module
semantic version `0.25.1`.

Offline Verifier V2 corrected that semantic-version comparator and executed as
Kaggle saved version `341096416`. V2 passed every required role except
`vllm_native_extension`. That role imported `vllm._C` and failed with
`ModuleNotFoundError`.

Exact vLLM `v0.25.1` CUDA source/build reconciliation established that the CUDA
platform imports `vllm._C_stable_libtorch`; the historical `vllm._C` probe is
not the target CUDA-platform native-extension contract. Therefore the V2
failure does not establish exact-runtime incompatibility.

The V2 evidence also repeatedly emitted a `sitecustomize` startup warning for
missing `wrapt`, including on probes that otherwise passed. Historical
AuraGateway work had already established stronger startup and loader controls:

- remove `PYTHONPATH` and `PYTHONHOME`;
- set `PYTHONNOUSERSITE=1`;
- start target Python with `-S` and a controlled site bootstrap;
- install controlled `sitecustomize` and `usercustomize` sentinels before
  `site.main()`;
- remove non-target site/dist-package paths;
- prepend target NVIDIA libraries before inherited loader paths;
- allow the real NVIDIA driver path explicitly;
- reject CUDA stub resolution.

Those historical controls are design evidence, not current-line qualification.

## Decision

Accept V2 as immutable diagnostic evidence whose terminal failure was caused by
a verifier harness defect:

```text
classification=STALE_VERSION_BOUND_NATIVE_EXTENSION_PROBE
root_cause_status=ESTABLISHED
v2_repository_disposition=ACCEPTED_DIAGNOSTIC_FAILURE
runtime_incompatibility_established=false
```

Freeze the next verifier around a capability contract rather than another
private-symbol guess.

The minimum current-line capability boundary before exact-runtime P5/P6 is:

```text
ARTIFACT_CLOSURE
    ↓
OFFLINE_INSTALLATION_CLOSURE
    ↓
CONTROLLED_PYTHON_STARTUP_CLOSURE
    ↓
NATIVE_EXTENSION_INVENTORY
    ↓
NATIVE_LOADER_CLOSURE_AND_PROVENANCE
    ↓
VLLM_0_25_1_CUDA_PLATFORM_CAPABILITY
```

The current CUDA native-module requirement is:

```text
vllm._C_stable_libtorch
```

The final offline verifier must reuse the historically proven controlled-startup
and target-first loader policies, rebound to the exact 196-wheel final runtime.
It must prove native origins rather than treating a successful import alone as
sufficient.

Permitted ambient native dependency:

```text
real NVIDIA driver path under /usr/local/nvidia/lib64
```

Prohibited evidence shortcuts:

```text
CUDA stubs
unapproved ambient Python-package native libraries
successful native import with unknown provenance
```

The reconciliation itself performs no runtime execution and issues no execution
authorization.

## Alternatives considered

### Patch V2 from `vllm._C` to `vllm._C_stable_libtorch` and rerun immediately

Rejected. Two verifier false negatives and one confirmed stale critical probe
trigger the verifier-reconciliation circuit breaker. A symbol-only patch would
leave Python startup and native-loader provenance unresolved.

### Treat the `sitecustomize` / `wrapt` warning as causal and install `wrapt`

Rejected. The warning occurs on otherwise successful probes. Its causal role
in the V2 native failure is unproven. Installing a dependency to silence a
warning would change the frozen runtime without evidence.

### Promote historical CUDA 12.9 runtime evidence directly

Rejected. Historical evidence proves useful controls and stronger predecessor
capabilities, but it does not qualify the current vLLM `0.25.1+cu129` / Torch
`2.11.0+cu129` lineage.

### Skip current-line native verification and move directly to exact-runtime P5/P6

Rejected. PR #211 and V17 explicitly require the exact planned runtime lineage
to close its final offline/native prerequisite before current-line P5/P6 can be
accepted. Historical P5/P6 remains diagnostic evidence only.

## Consequences

After this reconciliation is merged:

```text
exact_runtime_offline_verified=false
p5_p6_exact_runtime_requalified=false
runtime_execution_authorized=false
pilot_execution_authorized=false
final_measured_abc_execution_authorized=false
next_expensive_execution_permitted=false
```

The next legal engineering gate is:

```text
design_and_implement_final_preflight_v3_exact_runtime_offline_verifier_from_reconciled_capability_contract
```

That next tranche may implement the final offline verifier, but runtime
execution remains a separate governed transition after implementation is merged
and validated.

## Non-claims

This ADR does not prove:

- exact-runtime offline/native compatibility;
- worker startup or model load;
- exact-runtime P5 cache reuse/reset behavior;
- exact-runtime P6 dual-worker isolation;
- variance-pilot readiness;
- measured A/B/C effect;
- deployment or production readiness.
