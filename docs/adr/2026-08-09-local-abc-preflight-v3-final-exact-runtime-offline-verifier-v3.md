# ADR: Final preflight-v3 exact-runtime offline verifier V3

Date: 2026-08-09

## Status

Proposed for repository implementation acceptance. Execution is not authorized by this ADR.

## Authority

Current sequencing authority is the merged repository state at
`581a65c7856bc7530b60efcd8536f5562cd8ea15` plus the accepted preflight-v3
runtime-verifier reconciliation V1.

The July Controlled Local A/B/C Completion Extension PRD remains historical
North-Star and experiment-design context. It is not the current exact-runtime
qualification stage map.

## Context

Offline verifier V1 produced a false negative by conflating the vLLM
distribution identity `0.25.1+cu129` with module semantic version `0.25.1`.
Offline verifier V2 corrected that comparator but failed only because it treated
`vllm._C` as the required CUDA native extension.

The accepted reconciliation establishes:

```text
required CUDA native module=vllm._C_stable_libtorch
legacy V2 native probe=vllm._C
V2 repository disposition=ACCEPTED_DIAGNOSTIC_FAILURE
runtime incompatibility established=false
```

For vLLM `v0.25.1`, the CUDA platform's `import_kernels()` imports
`vllm._C_stable_libtorch`; the legacy `_C` target is ROCm-only in that release's
CMake contract. The same build contract expects Torch `2.11.0` for CUDA.

Historical AuraGateway work also established stronger process controls than V2
used: controlled `-S` Python startup with sentinel customization modules,
target-first native-library ordering, CUDA-stub rejection, and explicit driver
provenance. Those controls are design evidence only and must be rebound to the
exact 196-wheel final runtime.

## Decision

Implement one final bounded offline verifier around the six reconciled layers:

```text
L0 ARTIFACT_CLOSURE
L1 OFFLINE_INSTALLATION_CLOSURE
L2 CONTROLLED_PYTHON_STARTUP_CLOSURE
L3 NATIVE_EXTENSION_INVENTORY
L4 NATIVE_LOADER_CLOSURE_AND_PROVENANCE
L5 VLLM_0_25_1_CUDA_PLATFORM_CAPABILITY
```

The verifier reuses V2's exact 196-wheel input validation and hash-locked
base-pip-to-target installation. It changes the runtime boundary as follows.

### Controlled Python startup

Every target-runtime Python probe after installation runs as:

```text
target-python -S
+ controlled site bootstrap
+ sentinel sitecustomize/usercustomize
+ site.main()
+ removal of non-target site/dist-package paths
```

The subprocess environment must:

- remove `PYTHONPATH`;
- remove `PYTHONHOME`;
- remove `LD_PRELOAD`;
- set `PYTHONNOUSERSITE=1`;
- remain offline;
- bind `VIRTUAL_ENV` to the target root.

### Native loader ordering

Construct `LD_LIBRARY_PATH` from:

```text
target nvidia/*/lib directories
→ target torch/lib
→ /usr/local/nvidia/lib64
→ filtered inherited system paths
```

Reject inherited CUDA stub/compat paths and external Python package native
library directories.

### Native inventory

Require exactly one target vLLM shared object matching:

```text
vllm/_C_stable_libtorch*.so
```

`vllm._C` is not a required CUDA probe. Optional vLLM extensions remain
observational only.

### Loader closure and provenance

A successful import is necessary but insufficient.

Require both:

1. static `ldd` closure for the required `_C_stable_libtorch` shared object;
2. dynamic `/proc/self/maps` provenance after Torch CUDA and the required vLLM
   extension are loaded.

Fail on:

- unresolved required shared libraries;
- CUDA stub/compat origins;
- native libraries from non-target Python package trees;
- Torch native libraries outside target `torch/lib`;
- NVIDIA runtime libraries outside target `nvidia/*`;
- CUDA driver origin outside `/usr/local/nvidia/lib64`;
- required vLLM extension origin outside the target vLLM package.

System runtime libraries such as glibc and the ELF loader are permitted. The
verifier does not incorrectly require every OS dependency to be inside the
Python target.

### CUDA platform capability

After native import and provenance pass, invoke vLLM's CUDA platform kernel
import path and require:

- CUDA available;
- exactly two T4 devices;
- `vllm._C_stable_libtorch` loaded;
- exact Torch/CUDA/vLLM runtime identities already passed upstream.

## Failure taxonomy

The evidence harness preserves the existing per-role states:

```text
PASSED
FAILED
BLOCKED_BY_UPSTREAM_FAILURE
NOT_EXECUTED
```

The first failed required role remains queryable. Diagnostic detail must be
sufficient to distinguish:

```text
artifact identity failure
offline installation failure
controlled startup isolation failure
required native file missing/ambiguous
static linker unresolved dependency
prohibited native origin
native extension import/ABI failure
CUDA driver/runtime failure
vLLM CUDA platform capability failure
```

No downstream failure may be rewritten as a generic runtime incompatibility.

## Safety boundary

This verifier permits zero:

```text
model loads
worker startups
model requests
benchmark trajectories
P5/P6 execution
variance-pilot execution
measured A/B/C execution
```

Implementation acceptance does not authorize verifier execution. A future T4
run requires a separate execution-authorization transition after this tranche
is merged and statically validated.

## Alternatives rejected

### Patch V2 and rerun

Rejected. It would repeat the symbol-only remediation pattern that already
produced two false negatives and would leave provenance unproved.

### Require all `ldd` dependencies under the target root

Rejected. That would misclassify legitimate OS runtime libraries such as glibc
and the ELF loader as contamination and create another verifier false negative.

### Silence `sitecustomize` by installing `wrapt`

Rejected. The reconciliation explicitly leaves the warning's causal role
unproven. Runtime mutation without evidence would violate the frozen closure.

### Promote historical loader evidence

Rejected. Historical evidence supplies implementation controls but cannot
qualify the exact current vLLM `0.25.1+cu129` / Torch `2.11.0+cu129` lineage.

## Consequence

After repository implementation acceptance:

```text
implementation_status=IMPLEMENTED_NOT_EXECUTED
exact_runtime_offline_verified=false
p5_p6_exact_runtime_requalified=false
runtime_execution_authorized=false
pilot_execution_authorized=false
final_measured_abc_execution_authorized=false
next_expensive_execution_permitted=false
```

The next legal transition is a separate bounded execution-authorization review
for this exact verifier implementation.
