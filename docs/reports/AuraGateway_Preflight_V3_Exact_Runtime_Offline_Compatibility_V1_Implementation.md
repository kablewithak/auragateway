# AuraGateway Preflight-v3 Exact Runtime Offline Compatibility V1

## Implementation status

`IMPLEMENTED_NOT_EXECUTED`

## Input authority

```text
materialization_acceptance_sha256=042150fdc207e0f0a13f3c40209fc308b133b7abbbef5980130d23ec64c51725
accepted_materializer_script_version_id=341083505
resolution_lock_sha256=1294394ac476336b103b036d8654a49e4ae78c25c912ca5729cd94f982384f3c
package_count=196
sha_manifest_entry_count=200
total_wheel_bytes=6164913809
```

## Verification boundary

The verifier validates the entire accepted wheelhouse before installation:

1. unique materializer output discovery;
2. exact top-level topology;
3. no symlinks;
4. exact six control-file hashes;
5. exact frozen resolution lock;
6. exact 196-wheel filename set;
7. streaming verification of all 200 SHA-manifest entries;
8. exact total wheel-byte identity;
9. deterministic reconstruction of both install lock files.

Only then may target installation begin.

## Installation harness

The target is created with `venv --without-pip`. Base pip is used only as the
executor through its global `--python <target>` interface.

Installation is constrained by:

```text
--no-index
--no-cache-dir
--no-deps
--find-links <accepted-wheelhouse>
--require-hashes
-r requirements.lock.txt
```

This avoids fresh dependency solving and prevents network-backed acquisition.

## Runtime probes

The harness separately records:

```text
base_python_runtime
base_pip_import
base_distribution_snapshot_before
gpu_topology
target_environment_creation
target_runtime_identity_before_install
base_pip_python_target_support
offline_hash_locked_install_via_base_pip
target_distribution_inventory
target_dependency_check_via_base_pip
python_runtime
torch_family_runtime
transformers_runtime
triton_distribution
vllm_distribution
vllm_module
vllm_native_extension
base_distribution_snapshot_after
```

Every role uses one of:

```text
PASSED
FAILED
BLOCKED_BY_UPSTREAM_FAILURE
NOT_EXECUTED
```

## Privacy and safety

No credentials, customer data, model snapshot, raw prompts, or benchmark
payloads are required. Evidence stores bounded subprocess excerpts and replaces
Kaggle/home paths with generic tokens.

## Current state

```text
wheelhouse_materialized=true
exact_runtime_materialized=true
exact_runtime_offline_verified=false
p5_p6_exact_runtime_requalified=false
runtime_execution_authorized=false
pilot_execution_authorized=false
final_measured_abc_execution_authorized=false
```

## Next gate

`merge_then_execute_preflight_v3_exact_runtime_offline_compatibility_verifier_v1`
