# Runbook: preflight-v3 exact-runtime materialization acceptance V1

## Accepted immutable materializer output

Kaggle script version:

```text
341083505
```

Materialization evidence ZIP SHA-256:

```text
6d97b933473064a71fafe790ab9d8a5bf87d9805d8666880b209123745a5d6df
```

Exact resolution lock SHA-256:

```text
1294394ac476336b103b036d8654a49e4ae78c25c912ca5729cd94f982384f3c
```

The accepted output contains exactly 196 wheel files totaling 6,164,913,809 bytes.

## Reuse rule

Do not rerun the accepted materializer.

The saved Kaggle version is the candidate wheelhouse source for the next verifier.

## Next verifier boundary

The next tranche must implement a fresh verifier with:

```text
Accelerator: T4 x2
Internet: Off
Secrets: None
Inputs: exactly the accepted saved materializer output
```

The verifier must first prove complete wheelhouse integrity before attempting installation:

1. validate exact top-level topology;
2. verify the exact resolution lock SHA;
3. verify the 200-entry SHA manifest;
4. stream-hash all 196 wheel files;
5. prove wheel filename set equality against the frozen lock;
6. prove wheel SHA equality against the frozen lock;
7. prove total wheel-byte identity;
8. only then begin an isolated offline install.

Installation and runtime checks must be separately observable roles. At minimum preserve:

```text
input_validation
base_python_runtime
base_pip_import
base_distribution_snapshot_before
gpu_topology
target_environment_creation
offline_hash_locked_install
target_distribution_inventory
target_dependency_check
torch_import
torch_version
torch_cuda_version
cuda_runtime_visibility
vllm_distribution_version
vllm_python_import
vllm_native_extension_import
base_distribution_snapshot_after
```

Downstream roles must distinguish:

```text
PASSED
FAILED
BLOCKED_BY_UPSTREAM_FAILURE
NOT_EXECUTED
```

## Stop policy

A failure is evidence. Preserve the first saved verifier version and do not edit/rerun it to force
a pass.

No model loading, worker startup, model request, P5/P6 qualification, variance pilot, or measured
A/B/C execution is authorized by the materialization acceptance.
